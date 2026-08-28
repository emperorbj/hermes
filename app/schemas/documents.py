import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocumentStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    detail: str
    id: uuid.UUID
