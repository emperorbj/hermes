import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Chunk, Document, Role, User
from app.schemas.documents import DeleteResponse, DocumentOut
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.parsing import extract_text, resolve_content_type
from app.services.vector_store import delete_document_vectors, upsert_chunks

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    content_type = resolve_content_type(file.filename)
    if content_type is None:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF or DOCX.")

    contents = await file.read()
    document = Document(
        filename=file.filename,
        content_type=content_type,
        size_bytes=len(contents),
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        text = extract_text(contents, content_type)
        chunks = chunk_text(text)
        embeddings = embed_texts(chunks)
        for i, chunk in enumerate(chunks):
            db.add(Chunk(document_id=document.id, chunk_index=i, text=chunk))
        db.commit()

        upsert_chunks(
            document_id=str(document.id),
            filename=document.filename,
            uploaded_by=str(current_user.id),
            chunks=chunks,
            embeddings=embeddings,
        )
    except Exception as exc:
        db.delete(document)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to process document") from exc

    return document


@router.get("/", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document_vectors(str(document_id))
    db.delete(document)
    db.commit()
    return DeleteResponse(detail="Document deleted successfully", id=document_id)
