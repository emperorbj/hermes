import sys
import uuid
from pathlib import Path

from app.database import SessionLocal
from app.models import Document, DocumentStatus
from app.services.parsing import resolve_content_type
from app.services.storage import upload_file
from app.tasks import process_document_task

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: uv run python test_process_document_task.py <path-to-file> <uploaded-by-user-id>")
        sys.exit(1)

    path = Path(sys.argv[1])
    uploaded_by = sys.argv[2]

    content_type = resolve_content_type(path.name)
    if content_type is None:
        print(f"Unsupported extension: {path.suffix}")
        sys.exit(1)

    file_bytes = path.read_bytes()

    db = SessionLocal()
    document = Document(
        filename=path.name,
        content_type=content_type,
        size_bytes=len(file_bytes),
        status=DocumentStatus.PROCESSING,
        uploaded_by=uuid.UUID(uploaded_by),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    document_id = str(document.id)
    db.close()

    r2_key = f"uploads/{document_id}/{path.name}"
    upload_file(r2_key, file_bytes)
    print(f"Uploaded to R2 at key={r2_key}")
    print(f"Document created: id={document_id}, status=processing")

    result = process_document_task.delay(
        document_id=document_id,
        r2_key=r2_key,
        filename=path.name,
        content_type=content_type,
        uploaded_by=uploaded_by,
    )
    print(f"Task dispatched, id={result.id}")
    print("Watch the worker's terminal, then query the documents table to confirm status changed to 'ready'.")
