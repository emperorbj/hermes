from app.services.bm25 import build_bm25_retriever
from app.services.embeddings import embed_query
from app.services.reranking import rerank_candidates
from app.services.vector_store import query_similar_chunks


def hybrid_retrieve(query: str, top_k: int = 5) -> list[dict]:
    query_vector = embed_query(query)
    dense_results = query_similar_chunks(query_vector, top_k=top_k)

    bm25_retriever = build_bm25_retriever(k=top_k)
    lexical_results = bm25_retriever.invoke(query)

    candidates: dict[tuple[str, int], dict] = {}

    for result in dense_results:
        metadata = result["metadata"]
        key = (metadata["document_id"], metadata["chunk_index"])
        candidates[key] = {
            "document_id": metadata["document_id"],
            "chunk_index": metadata["chunk_index"],
            "filename": metadata.get("filename"),
            "text": metadata["text"],
            "sources": ["dense"],
        }

    for doc in lexical_results:
        key = (doc.metadata["document_id"], doc.metadata["chunk_index"])
        if key in candidates:
            candidates[key]["sources"].append("lexical")
        else:
            candidates[key] = {
                "document_id": doc.metadata["document_id"],
                "chunk_index": doc.metadata["chunk_index"],
                "filename": doc.metadata.get("filename"),
                "text": doc.page_content,
                "sources": ["lexical"],
            }

    return list(candidates.values())


def retrieve_and_rerank(query: str, top_k: int = 5) -> list[dict]:
    # NOTE: no caching here yet — deliberately deferred (see rag-project-architecture.md's
    # Caching Strategy section). When added, this must be keyed on query + top_k + the
    # active access-level/department filters (once those exist), never query alone,
    # or cached results could leak across users with different permissions.
    candidates = hybrid_retrieve(query, top_k=top_k)
    return rerank_candidates(query, candidates, top_n=top_k)
