import sys
import uuid
from pathlib import Path

from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts
from app.services.parsing import extract_text, resolve_content_type
from app.services.vector_store import index, upsert_chunks

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_vector_store.py <path-to-file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    content_type = resolve_content_type(path.name)
    if content_type is None:
        print(f"Unsupported extension: {path.suffix}")
        sys.exit(1)

    text = extract_text(path.read_bytes(), content_type)
    chunks = chunk_text(text)
    embeddings = embed_texts(chunks)

    document_id = str(uuid.uuid4())
    print(f"Upserting {len(chunks)} chunks under document_id={document_id}")

    upsert_chunks(
        document_id=document_id,
        filename=path.name,
        uploaded_by="test-script",
        chunks=chunks,
        embeddings=embeddings,
    )

    stats = index.describe_index_stats()
    print(f"Index now reports {stats.total_vector_count} total vectors.")
