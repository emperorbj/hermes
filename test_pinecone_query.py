import sys

from app.services.embeddings import embed_query
from app.services.vector_store import query_similar_chunks

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_pinecone_query.py <query text>")
        sys.exit(1)

    query = sys.argv[1]
    query_vector = embed_query(query)
    results = query_similar_chunks(query_vector)

    print(f"Got {len(results)} results for query: {query!r}")
    for i, result in enumerate(results):
        print(f"\n---- Result {i} (score={result['score']:.4f}, document_id={result['metadata']['document_id']}) ----")
        print(result["metadata"]["text"][:300])
