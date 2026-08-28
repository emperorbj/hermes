import sys

from app.services.bm25 import build_bm25_retriever

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_bm25.py <query text>")
        sys.exit(1)

    query = sys.argv[1]
    retriever = build_bm25_retriever()
    results = retriever.invoke(query)

    print(f"Got {len(results)} results for query: {query!r}")
    for i, doc in enumerate(results):
        print(f"\n---- Result {i} (document_id={doc.metadata['document_id']}, chunk_index={doc.metadata['chunk_index']}) ----")
        print(doc.page_content[:300])
