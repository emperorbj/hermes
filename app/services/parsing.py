from io import BytesIO

from docx import Document as DocxFile
from pypdf import PdfReader

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = DocxFile(BytesIO(file_bytes))
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            if row_text.strip(" |"):
                parts.append(row_text)
    return "\n".join(parts)


def extract_text(file_bytes: bytes, content_type: str) -> str:
    if content_type == PDF_CONTENT_TYPE:
        return extract_text_from_pdf(file_bytes)
    if content_type == DOCX_CONTENT_TYPE:
        return extract_text_from_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {content_type}")
