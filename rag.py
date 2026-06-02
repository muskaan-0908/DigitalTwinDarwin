
import os
import re
import hashlib
import math
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# ── Optional: CrossEncoder for reranking ─────────────────────────────────────
try:
    from sentence_transformers import CrossEncoder
    _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    _HAS_CROSS_ENCODER = True
except Exception:
    _HAS_CROSS_ENCODER = False
    print("[rag] CrossEncoder not available — reranking disabled. "
          "pip install sentence-transformers  to enable it.")

# ── ChromaDB setup ────────────────────────────────────────────────────────────

client = chromadb.PersistentClient(path="./chroma_db")

emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# ── Source labels ─────────────────────────────────────────────────────────────

SOURCE_LABELS = {
    "origin_of_species":        "On the Origin of Species (1859)",
    "voyage_of_the_beagle":     "The Voyage of the Beagle (1839)",
    "descent_of_man":           "The Descent of Man (1871)",
    "autobiography":            "My Autobiography",
    "expression_of_emotions":   "The Expression of the Emotions in Man and Animals (1872)",
    "variation_animals_plants": "The Variation of Animals and Plants under Domestication (1868)",
    "orchids":                  "On the Various Contrivances by which Orchids are Fertilised (1862)",
    "earthworms":               "The Formation of Vegetable Mould through the Action of Worms (1881)",
    "letters":                  "Darwin's Correspondence",
    "barnacles":                "A Monograph on the Sub-class Cirripedia (1851-1854)",
}


def _source_label(source_name: str) -> str:
    return SOURCE_LABELS.get(source_name, source_name.replace("_", " ").title())


# ── Collection ────────────────────────────────────────────────────────────────

def get_or_create_collection(scientist_name: str):
    return client.get_or_create_collection(
        name=scientist_name.lower().replace(" ", "_"),
        embedding_function=emb_fn,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 3 — BM25 in-memory index
# ─────────────────────────────────────────────────────────────────────────────

class BM25Index:
    """
    Lightweight Okapi BM25 implementation, no dependencies.

    BM25 score(query q, document d):
        sum over query terms t of:
            IDF(t) * tf(t,d)*(k1+1) / (tf(t,d) + k1*(1 - b + b*|d|/avgdl))

    k1=1.5, b=0.75 are standard defaults.
    """

    def __init__(self, docs, ids, metas, k1=1.5, b=0.75):
        self.ids   = ids
        self.metas = metas
        self.k1    = k1
        self.b     = b

        self.tokenised = [self._tok(d) for d in docs]
        self.n         = len(docs)
        self.avgdl     = sum(len(t) for t in self.tokenised) / max(self.n, 1)

        self.df = {}
        for tokens in self.tokenised:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1

    @staticmethod
    def _tok(text):
        return re.findall(r"\b[a-z]{2,}\b", text.lower())

    def _idf(self, term):
        df = self.df.get(term, 0)
        return math.log((self.n - df + 0.5) / (df + 0.5) + 1)

    def search(self, query, n=10):
        q_terms = self._tok(query)
        scores  = []
        for idx, tokens in enumerate(self.tokenised):
            tf_map = {}
            for t in tokens:
                tf_map[t] = tf_map.get(t, 0) + 1
            dl    = len(tokens)
            score = 0.0
            for term in q_terms:
                tf = tf_map.get(term, 0)
                if tf == 0:
                    continue
                num   = tf * (self.k1 + 1)
                den   = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += self._idf(term) * num / den
            scores.append((idx, score))
        scores.sort(key=lambda x: -x[1])
        return [s for s in scores[:n] if s[1] > 0]


_bm25_index      = None
_bm25_doc_store  = []


def _get_bm25(collection):
    global _bm25_index, _bm25_doc_store
    if _bm25_index is not None:
        return _bm25_index
    try:
        if collection.count() == 0:
            return None
        result         = collection.get(include=["documents", "metadatas"])
        docs           = result["documents"]
        _bm25_doc_store = docs
        _bm25_index    = BM25Index(docs, result["ids"], result["metadatas"])
        print(f"[rag] BM25 index built over {len(docs)} chunks.")
        return _bm25_index
    except Exception as e:
        print(f"[rag] BM25 build failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 1 — Query Expansion
# ─────────────────────────────────────────────────────────────────────────────

def _expand_query(query: str) -> list:
    """Generate 2 alternative search queries via Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return [query]
    try:
        genai.configure(api_key=api_key)
        model  = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            f"You are helping retrieve passages from Charles Darwin's 19th-century writings.\n"
            f"Original question: {query}\n\n"
            f"Write exactly 2 alternative search queries using different vocabulary "
            f"that seek the same information. One should use Victorian scientific terminology. "
            f"Return only the 2 queries, one per line, no numbering, no explanation."
        )
        resp    = model.generate_content(prompt)
        lines   = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
        return [query] + lines[:2]
    except Exception:
        return [query]


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 2 — HyDE (Hypothetical Document Embedding)
# ─────────────────────────────────────────────────────────────────────────────

def _hyde_query(query: str) -> str:
    """
    Generate a short fake Darwin passage that would answer the query.
    Embedding this passage finds better matches than embedding the question.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return query
    try:
        genai.configure(api_key=api_key)
        model  = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            f"Write a short passage (3-5 sentences) as Charles Darwin might have written it "
            f"in the 19th century that directly answers:\n\n{query}\n\n"
            f"Write only the passage in Darwin's voice, no preamble."
        )
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception:
        return query


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 4 — MMR (Maximal Marginal Relevance)
# ─────────────────────────────────────────────────────────────────────────────

def _cosine(a, b):
    dot    = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b + 1e-9)


def _mmr(query_emb, candidate_docs, candidate_metas, doc_embs, n=5, lam=0.6):
    """
    Iteratively pick the doc that maximises:
        lambda * relevance_to_query - (1-lambda) * max_similarity_to_selected

    lam=0.6 gives a good relevance/diversity balance.
    """
    if not candidate_docs:
        return [], []

    selected_idx  = []
    selected_docs = []
    selected_meta = []
    remaining     = list(range(len(candidate_docs)))

    for _ in range(min(n, len(candidate_docs))):
        best_score = -1e9
        best_i     = remaining[0]

        for i in remaining:
            rel = _cosine(query_emb, doc_embs[i])
            red = max((_cosine(doc_embs[i], doc_embs[j]) for j in selected_idx), default=0.0)
            score = lam * rel - (1 - lam) * red
            if score > best_score:
                best_score = score
                best_i     = i

        selected_idx.append(best_i)
        selected_docs.append(candidate_docs[best_i])
        selected_meta.append(candidate_metas[best_i])
        remaining.remove(best_i)

    return selected_docs, selected_meta


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 5 — Cross-encoder reranking
# ─────────────────────────────────────────────────────────────────────────────

def _rerank(query, docs, metas):
    if not _HAS_CROSS_ENCODER or not docs:
        return docs, metas
    try:
        scores = _cross_encoder.predict([(query, d) for d in docs])
        ranked = sorted(zip(scores, docs, metas), key=lambda x: -x[0])
        return [d for _, d, _ in ranked], [m for _, _, m in ranked]
    except Exception:
        return docs, metas


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE 6 — Contextual Compression
# ─────────────────────────────────────────────────────────────────────────────

def _compress(query, doc, max_sentences=4):
    """
    Keep only the top-scoring sentences from a chunk.
    Scoring = keyword overlap between sentence and query.
    No API call needed — pure Python.
    """
    sentences = re.split(r'(?<=[.!?])\s+', doc.strip())
    if len(sentences) <= max_sentences:
        return doc

    q_words = set(re.findall(r"\b[a-z]{3,}\b", query.lower()))
    if not q_words:
        return doc

    scored = []
    for i, sent in enumerate(sentences):
        s_words = set(re.findall(r"\b[a-z]{3,}\b", sent.lower()))
        overlap = len(q_words & s_words) / (len(q_words) + 1e-9)
        scored.append((i, overlap))

    top = sorted(
        sorted(scored, key=lambda x: -x[1])[:max_sentences],
        key=lambda x: x[0]
    )
    return " ".join(sentences[i] for i, _ in top)


# ── Retrieval cache ───────────────────────────────────────────────────────────

_retrieval_cache = {}
_CACHE_MAX       = 100


def _cache_set(key, value):
    if len(_retrieval_cache) >= _CACHE_MAX:
        del _retrieval_cache[next(iter(_retrieval_cache))]
    _retrieval_cache[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# MAIN retrieve() — full pipeline
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(query: str, n_results: int = 5) -> list:
    """
    Pipeline:
        query
          ├─► Query Expansion  (3 variants)
          ├─► HyDE             (1 hypothetical passage)
          ├─► Vector Search    (all 4 queries merged, deduped)
          ├─► BM25 Search      (keyword hits merged in)
          ├─► MMR              (diversify the candidate pool)
          ├─► Cross-encoder    (rerank by true relevance)
          └─► Compression      (trim to relevant sentences)
                └─► labelled passages ["[Source]\ntext...", ...]
    """
    cache_key = query.strip().lower()
    if cache_key in _retrieval_cache:
        return _retrieval_cache[cache_key]

    collection = get_or_create_collection("charles_darwin")
    total      = collection.count()
    if total == 0:
        return []

    fetch_n = min(n_results * 4, total)

    # Step 1 + 2: build all query variants
    variants  = _expand_query(query)
    hyde_q    = _hyde_query(query)
    all_q     = list(dict.fromkeys(variants + [hyde_q]))  # dedup, keep order

    # Step 3: vector search for all variants, merged + deduped
    seen_ids  = set()
    all_docs  = []
    all_metas = []

    for q in all_q:
        try:
            res = collection.query(query_texts=[q], n_results=fetch_n)
            for doc, meta, doc_id in zip(
                res["documents"][0], res["metadatas"][0], res["ids"][0]
            ):
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
                    all_metas.append(meta)
        except Exception:
            continue

    # Step 3b: BM25 hybrid
    bm25 = _get_bm25(collection)
    if bm25 is not None:
        for idx, _score in bm25.search(query, n=fetch_n):
            try:
                doc_id = bm25.ids[idx]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(_bm25_doc_store[idx])
                    all_metas.append(bm25.metas[idx])
            except IndexError:
                continue

    if not all_docs:
        return []

    # Step 4: MMR
    try:
        doc_embs   = emb_fn(all_docs)
        query_emb  = emb_fn([query])[0]
        mmr_docs, mmr_metas = _mmr(
            query_emb, all_docs, all_metas, doc_embs, n=n_results * 2
        )
    except Exception:
        mmr_docs  = all_docs[:n_results * 2]
        mmr_metas = all_metas[:n_results * 2]

    # Step 5: cross-encoder reranking
    reranked_docs, reranked_metas = _rerank(query, mmr_docs, mmr_metas)

    # Step 6: compression + source labelling
    labelled = []
    for doc, meta in zip(reranked_docs[:n_results], reranked_metas[:n_results]):
        compressed = _compress(query, doc, max_sentences=4)
        label      = meta.get("source_label") or _source_label(meta.get("source", "unknown"))
        labelled.append(f"[{label}]\n{compressed.strip()}")

    _cache_set(cache_key, labelled)
    return labelled


# ── Ingest (unchanged API) ────────────────────────────────────────────────────

def _content_id(source_name, chunk_type, text):
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    return f"{source_name}_{chunk_type}_{digest}"


def _invalidate_bm25():
    global _bm25_index, _bm25_doc_store
    _bm25_index     = None
    _bm25_doc_store = []
    _retrieval_cache.clear()


def ingest_text_file(filepath, scientist_name, source_name):
    print(f"Reading {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    _chunk_and_store(text, scientist_name, source_name)
    _invalidate_bm25()


def ingest_pdf(filepath, scientist_name, source_name):
    print(f"Reading PDF {filepath}...")
    reader    = PyPDF2.PdfReader(filepath)
    full_text = "\n".join(
        p.extract_text() for p in reader.pages if p.extract_text()
    )
    _chunk_and_store(full_text, scientist_name, source_name)
    _invalidate_bm25()


def _chunk_and_store(text, scientist_name, source_name):
    large_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    small_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    large_chunks = large_splitter.split_text(text)
    small_chunks = small_splitter.split_text(text)
    label        = _source_label(source_name)
    collection   = get_or_create_collection("charles_darwin")

    collection.upsert(
        documents = large_chunks + small_chunks,
        ids       = [_content_id(source_name, "large", c) for c in large_chunks] +
                    [_content_id(source_name, "small", c) for c in small_chunks],
        metadatas = [{"source": source_name, "source_label": label, "chunk_type": "large"} for _ in large_chunks] +
                    [{"source": source_name, "source_label": label, "chunk_type": "small"} for _ in small_chunks],
    )
    print(f"  ✓ {label}: {len(large_chunks)} large + {len(small_chunks)} small chunks stored")