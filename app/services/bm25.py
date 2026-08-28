from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document as LCDocument

from app.database import SessionLocal
from app.models import Chunk, Document


def build_bm25_retriever(k: int = 5) -> BM25Retriever:
    db = SessionLocal()
    try:
        rows = db.query(Chunk, Document.filename).join(Document, Chunk.document_id == Document.id).all()
    finally:
        db.close()

    documents = [
        LCDocument(
            page_content=chunk.text,
            metadata={
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "filename": filename,
            },
        )
        for chunk, filename in rows
    ]

    retriever = BM25Retriever.from_documents(documents)
    retriever.k = k
    return retriever
