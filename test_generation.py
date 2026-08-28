import sys

from app.services.generation import generate_answer
from app.services.retrieval import retrieve_and_rerank

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_generation.py <question>")
        sys.exit(1)

    query = sys.argv[1]
    context_chunks = retrieve_and_rerank(query)
    print(f"Retrieved {len(context_chunks)} chunks for context.\n")

    result = generate_answer(query, context_chunks)
    print("---- Answer ----")
    print(result.answer)
    print("\n---- Citations (validated) ----")
    for citation in result.citations:
        print(f"document_id={citation.document_id}, chunk_index={citation.chunk_index}")
