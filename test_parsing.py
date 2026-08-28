import sys
from pathlib import Path

from app.services.parsing import extract_text, resolve_content_type

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_parsing.py <path-to-file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    content_type = resolve_content_type(path.name)
    if content_type is None:
        print(f"Unsupported extension: {path.suffix}")
        sys.exit(1)

    file_bytes = path.read_bytes()
    text = extract_text(file_bytes, content_type)
    print(f"Extracted {len(text)} characters.")
    print("---- First 700 characters ----")
    print(text[:700])
