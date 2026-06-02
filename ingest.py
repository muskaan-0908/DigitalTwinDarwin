import os
from rag import ingest_text_file, ingest_pdf, get_or_create_collection

SCIENTIST = "charles_darwin"
DATA_FOLDER = "./data"

def main():
    print("="*50)
    print("Ingesting Darwin's documents into ChromaDB...")
    print("="*50)

    
    collection = get_or_create_collection(SCIENTIST)
    before = collection.count()
    print(f"Chunks already in database: {before}\n")

    
    for filename in os.listdir(DATA_FOLDER):
        filepath = os.path.join(DATA_FOLDER, filename)
        source_name = filename.replace(".txt", "").replace(".pdf", "")

        if filename.endswith(".txt"):
            ingest_text_file(filepath, SCIENTIST, source_name)
        elif filename.endswith(".pdf"):
            ingest_pdf(filepath, SCIENTIST, source_name)
        else:
            print(f"  Skipping {filename} (not .txt or .pdf)")

    after = collection.count()
    print(f"\n{'='*50}")
    print(f"Added {after - before} new chunks.")
    print(f"Total chunks in database: {after}")


if __name__ == "__main__":
    main()


embeddings = model.encode(all_documents)
np.save("embeddings_cache.npy", embeddings)


embeddings = np.load("embeddings_cache.npy")