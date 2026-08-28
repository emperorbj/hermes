import sys
from pathlib import Path

from app.services.chunking import chunk_text
from app.services.parsing import extract_text, resolve_content_type

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_chunking.py <path-to-file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    content_type = resolve_content_type(path.name)
    if content_type is None:
        print(f"Unsupported extension: {path.suffix}")
        sys.exit(1)

    text = extract_text(path.read_bytes(), content_type)
    chunks = chunk_text(text)

    print(f"Split into {len(chunks)} chunks.")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n---- Chunk {i} ({len(chunk)} chars) ----")
        print(chunk)
