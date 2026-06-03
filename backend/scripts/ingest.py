#!/usr/bin/env python3.13
"""
EcoHome KB Ingestion Script
Loads markdown files from knowledge-base/, chunks them, embeds them
using HuggingFace, and stores them in ChromaDB.

Usage:
    pip install chromadb langchain langchain-community sentence-transformers
    python scripts/ingest.py
"""

import os
import sys
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = "ecohome-kb"
KB_PATH = Path(__file__).parent.parent.parent / "knowledge-base"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def main():
    print(f"EcoHome KB Ingestion")
    print(f"====================")
    print(f"KB path:    {KB_PATH}")
    print(f"ChromaDB:   http://{CHROMA_HOST}:{CHROMA_PORT}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Embed model:{EMBED_MODEL}")
    print()

    # ── 1. Load markdown files ────────────────────────────────────────────────
    print("Step 1: Loading markdown files...")
    md_files = [f for f in KB_PATH.glob("*.md") if f.name != "README.md"]
    if not md_files:
        print(f"ERROR: No .md files found in {KB_PATH}")
        sys.exit(1)
    print(f"  Found {len(md_files)} files: {[f.name for f in md_files]}")

    # ── 2. Chunk documents ────────────────────────────────────────────────────
    print("\nStep 2: Chunking documents...")
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    all_chunks = []
    all_ids = []
    all_metadatas = []

    for md_file in sorted(md_files):
        topic = md_file.stem  # e.g. "solar-panels"
        text = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{topic}-{i}")
            all_metadatas.append({
                "source": md_file.name,
                "topic": topic,
                "chunk_index": i,
            })
        print(f"  {md_file.name}: {len(chunks)} chunks")

    print(f"  Total chunks: {len(all_chunks)}")

    # ── 3. Embed ──────────────────────────────────────────────────────────────
    print(f"\nStep 3: Generating embeddings with {EMBED_MODEL}...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(all_chunks, show_progress_bar=True).tolist()
    print(f"  Embeddings generated: {len(embeddings)} vectors of dim {len(embeddings[0])}")

    # ── 4. Store in ChromaDB ──────────────────────────────────────────────────
    print(f"\nStep 4: Storing in ChromaDB collection '{COLLECTION_NAME}'...")
    import chromadb
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    # Delete existing collection if present (clean re-ingest)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection")
    except Exception:
        pass

    # Create collection via raw REST API to avoid embedding function metadata
    # being stored — Flowise provides query embeddings directly so no
    # server-side embedding function is needed.
    import httpx as _httpx
    _base = f"http://{CHROMA_HOST}:{CHROMA_PORT}/api/v2/tenants/default_tenant/databases/default_database"
    _r = _httpx.get(f"{_base}/collections/ecohome-kb")
    if _r.status_code == 200:
        _httpx.delete(f"{_base}/collections/ecohome-kb")
    _httpx.post(f"{_base}/collections", json={
        "name": COLLECTION_NAME,
        "metadata": {"hnsw:space": "cosine"}
    })

    collection = client.get_collection(name=COLLECTION_NAME)

    # Batch insert (ChromaDB recommends batches of ≤ 500)
    BATCH = 100
    for i in range(0, len(all_chunks), BATCH):
        collection.add(
            documents=all_chunks[i:i+BATCH],
            embeddings=embeddings[i:i+BATCH],
            ids=all_ids[i:i+BATCH],
            metadatas=all_metadatas[i:i+BATCH],
        )
    print(f"  Stored {collection.count()} chunks in ChromaDB")

    # ── 5. Smoke test ─────────────────────────────────────────────────────────
    print("\nStep 5: Smoke test query...")
    test_query = "How much does a solar panel system cost?"
    test_embedding = model.encode([test_query]).tolist()
    results = collection.query(
        query_embeddings=test_embedding,
        n_results=3,
    )
    print(f"  Query: '{test_query}'")
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  → [{meta['topic']}] {doc[:100]}...")

    print("\n✅ Ingestion complete!")

if __name__ == "__main__":
    main()
