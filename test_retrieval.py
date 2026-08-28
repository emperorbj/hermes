import sys

from app.services.retrieval import hybrid_retrieve

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_retrieval.py <query text>")
        sys.exit(1)

    query = sys.argv[1]
    results = hybrid_retrieve(query)

    print(f"Got {len(results)} merged candidates for query: {query!r}")
    for i, result in enumerate(results):
        print(
            f"\n---- Candidate {i} (sources={result['sources']}, "
            f"document_id={result['document_id']}, chunk_index={result['chunk_index']}) ----"
        )
        print(result["text"][:200])
