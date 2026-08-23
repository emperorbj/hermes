from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import require_role
from app.models import Role, User
from app.schemas.documents import UploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    contents = await file.read()
    return UploadResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        uploaded_by=current_user.email,
    )
