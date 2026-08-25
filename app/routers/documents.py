import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Document, Role, User
from app.schemas.documents import DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    document = Document(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
