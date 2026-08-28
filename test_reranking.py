import sys

from app.services.reranking import rerank_candidates
from app.services.retrieval import hybrid_retrieve

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_reranking.py <query text>")
        sys.exit(1)

    query = sys.argv[1]
    candidates = hybrid_retrieve(query)
    print(f"Hybrid retrieval returned {len(candidates)} candidates.")

    reranked = rerank_candidates(query, candidates)
    print(f"\nReranked to top {len(reranked)}:")
    for i, result in enumerate(reranked):
        print(
            f"\n---- Rank {i} (score={result['relevance_score']:.4f}, sources={result['sources']}, "
            f"document_id={result['document_id']}) ----"
        )
        print(result["text"][:200])
