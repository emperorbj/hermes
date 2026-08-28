import sys
import time

from app.services.retrieval import retrieve_and_rerank

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_retrieve_and_rerank.py <query text>")
        sys.exit(1)

    query = sys.argv[1]

    start = time.perf_counter()
    results = retrieve_and_rerank(query)
    elapsed = time.perf_counter() - start

    print(f"Got {len(results)} results in {elapsed:.3f}s.")
    for i, result in enumerate(results):
        print(f"\n---- Rank {i} (score={result['relevance_score']:.4f}) ----")
        print(result["text"][:150])
