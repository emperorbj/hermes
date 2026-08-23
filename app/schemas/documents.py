from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
