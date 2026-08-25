import sys
from pathlib import Path

from app.services.parsing import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE, extract_text

EXTENSION_TO_CONTENT_TYPE = {
    ".pdf": PDF_CONTENT_TYPE,
    ".docx": DOCX_CONTENT_TYPE,
}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python test_parsing.py <path-to-file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    content_type = EXTENSION_TO_CONTENT_TYPE.get(path.suffix.lower())
    if content_type is None:
        print(f"Unsupported extension: {path.suffix}")
        sys.exit(1)

    file_bytes = path.read_bytes()
    text = extract_text(file_bytes, content_type)
    print(f"Extracted {len(text)} characters.")
    print("---- First 500 characters ----")
    print(text[:700])
