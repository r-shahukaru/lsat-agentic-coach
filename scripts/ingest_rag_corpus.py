"""
scripts/ingest_rag_corpus.py

Splits local RAG corpus texts into chunks and upserts them
to Azure AI Search vector index via embeddings.
"""

import os
import glob
from dotenv import load_dotenv
from services.vector_search import VectorIndex

load_dotenv()

def main():
    idx = VectorIndex()  # uses your existing vector index setup

    for file in glob.glob("rag_corpus/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        base = os.path.basename(file)

        # Split into chunks ~500 words
        chunks = []
        lines = text.split("\n")
        current = []
        for line in lines:
            current.append(line)
            if len(" ".join(current).split()) > 400:
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))

        # Upsert into vector index
        for i, chunk in enumerate(chunks):
            meta = {"source": base, "chunk_index": i}
            idx.upsert_text(chunk, metadata=meta)

    print("RAG corpus ingested!")

if __name__ == "__main__":
    main()
