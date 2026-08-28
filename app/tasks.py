import uuid

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Chunk, Document, DocumentStatus
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.parsing import extract_text
from app.services.storage import delete_file, download_file
from app.services.vector_store import upsert_chunks


@celery_app.task
def hello_task(name: str) -> str:
    return f"Hello, {name}! Celery is working."


@celery_app.task
def process_document_task(
    document_id: str, r2_key: str, filename: str, content_type: str, uploaded_by: str
) -> None:
    document_uuid = uuid.UUID(document_id)
    db = SessionLocal()
    try:
        file_bytes = download_file(r2_key)

        text = extract_text(file_bytes, content_type)
        chunks = chunk_text(text)
        embeddings = embed_texts(chunks)

        for i, chunk in enumerate(chunks):
            db.add(Chunk(document_id=document_uuid, chunk_index=i, text=chunk))
        db.commit()

        upsert_chunks(
            document_id=document_id,
            filename=filename,
            uploaded_by=uploaded_by,
            chunks=chunks,
            embeddings=embeddings,
        )

        document = db.get(Document, document_uuid)
        document.status = DocumentStatus.READY
        db.commit()
    except Exception:
        db.rollback()
        document = db.get(Document, document_uuid)
        if document is not None:
            document.status = DocumentStatus.FAILED
            db.commit()
        raise
    finally:
        db.close()
        try:
            delete_file(r2_key)
        except Exception:
            pass  # best-effort cleanup — must never mask the real processing error above
