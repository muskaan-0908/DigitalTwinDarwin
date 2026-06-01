import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2





client = chromadb.PersistentClient(path="./chroma_db")

emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_or_create_collection(scientist_name):
    return client.get_or_create_collection(
        name=scientist_name.lower().replace(" ", "_"),
        embedding_function=emb_fn
    )






def ingest_text_file(filepath, scientist_name, source_name):
    print(f"Reading {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    _chunk_and_store(text, scientist_name, source_name)


def ingest_pdf(filepath, scientist_name, source_name):
    print(f"Reading PDF {filepath}...")
    reader = PyPDF2.PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    _chunk_and_store(text, scientist_name, source_name)


def _chunk_and_store(text, scientist_name, source_name):
    """
    IMPROVED CHUNKING STRATEGY:

    We use TWO chunk sizes:
    1. Large chunks (1000 chars) — for context-heavy questions
       that need a full paragraph to make sense
    2. Small chunks (300 chars) — for precise fact retrieval

    This is called "parent-child chunking" and dramatically
    improves retrieval quality. We store both.

    overlap=100 means chunks share 100 chars at the boundary
    so sentences that fall on a split aren't lost.
    """

    
    large_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        
        
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    
    small_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    large_chunks = large_splitter.split_text(text)
    small_chunks = small_splitter.split_text(text)

    collection = get_or_create_collection("charles_darwin")
    existing_count = collection.count()

    
    large_ids = [
        f"{source_name}_large_{i + existing_count}"
        for i in range(len(large_chunks))
    ]
    large_meta = [
        {"source": source_name, "chunk_type": "large"}
        for _ in large_chunks
    ]

    
    small_ids = [
        f"{source_name}_small_{i + existing_count + len(large_chunks)}"
        for i in range(len(small_chunks))
    ]
    small_meta = [
        {"source": source_name, "chunk_type": "small"}
        for _ in small_chunks
    ]

    collection.add(
        documents=large_chunks + small_chunks,
        ids=large_ids + small_ids,
        metadatas=large_meta + small_meta
    )

    print(f"  ✓ {source_name}: {len(large_chunks)} large + {len(small_chunks)} small chunks")








_retrieval_cache = {}

def retrieve(query, n_results=5):
    """
    IMPROVEMENTS over original:
    1. Cache — same query returns instantly on repeat
    2. n_results=5 instead of 4 — slightly more context
    3. We deduplicate results so near-identical chunks
       don't waste space in the prompt
    4. We prefer large chunks (more context per chunk)
    """

    
    cache_key = query.strip().lower()
    if cache_key in _retrieval_cache:
        return _retrieval_cache[cache_key]

    collection = get_or_create_collection("charles_darwin")

    if collection.count() == 0:
        return []

    
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count()),
        
        
        where={"chunk_type": "large"}
    )

    docs = results["documents"][0]

    
    
    deduped = _deduplicate(docs)

    
    _retrieval_cache[cache_key] = deduped
    return deduped


def _deduplicate(docs):
    """
    Simple deduplication: if two chunks share more than
    80% of their words, keep only the first one.
    """
    seen_words = []
    unique_docs = []

    for doc in docs:
        words = set(doc.lower().split())
        is_duplicate = False
        for prev_words in seen_words:
            
            overlap = len(words & prev_words) / len(words | prev_words)
            if overlap > 0.8:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_docs.append(doc)
            seen_words.append(words)

    return unique_docs