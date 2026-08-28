import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_INDEX_NAME = os.environ["PINECONE_INDEX_NAME"]

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)


def upsert_chunks(
    document_id: str,
    filename: str,
    uploaded_by: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    vectors = [
        {
            "id": f"{document_id}:{i}",
            "values": embedding,
            "metadata": {
                "document_id": document_id,
                "filename": filename,
                "uploaded_by": uploaded_by,
                "chunk_index": i,
                "text": chunk,
            },
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    index.upsert(vectors=vectors)


def delete_document_vectors(document_id: str) -> None:
    index.delete(filter={"document_id": {"$eq": document_id}})


def query_similar_chunks(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    response = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
    return [
        {"id": match.id, "score": match.score, "metadata": match.metadata}
        for match in response.matches
    ]
