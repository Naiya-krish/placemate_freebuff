"""Upload validation and text extraction (PDF, DOCX, optional OCR)."""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.errors import ApiError, UploadError

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


class PayloadTooLargeError(ApiError):
    def __init__(self) -> None:
        super().__init__(
            413, f"File exceeds the {settings.max_upload_mb} MB limit", "file_too_large"
        )


@dataclass
class ParsedDocument:
    text: str
    pages: int
    used_ocr: bool = False
    warnings: list[str] = field(default_factory=list)


def validate_upload(filename: str, content_type: str | None, data: bytes) -> str:
    """Validate extension, declared MIME and magic bytes. Returns normalised extension."""
    if not filename or not data:
        raise UploadError("A non-empty PDF or DOCX file is required", "empty_file")
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError()
    if len(data) < 16:
        raise UploadError("File is too small to be a valid document", "corrupt_file")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadError("Only PDF and DOCX resumes are accepted", "unsupported_type")
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_MIME:
        raise UploadError("Declared content type is not allowed", "unsupported_type")

    if ext == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise UploadError("File extension does not match its content", "magic_byte_mismatch")
        if b"%%EOF" not in data[-2048:]:
            raise UploadError("PDF appears truncated or corrupt", "corrupt_file")
    else:
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise UploadError("File extension does not match its content", "magic_byte_mismatch")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                raise UploadError("Not a valid DOCX document", "magic_byte_mismatch")
            if any(name.startswith("/") or ".." in name for name in names):
                raise UploadError("DOCX contains unsafe paths", "corrupt_file")
    return ext


def _extract_pdf(data: bytes) -> ParsedDocument:
    import fitz  # PyMuPDF

    warnings: list[str] = []
    text_parts: list[str] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UploadError("Could not read the PDF", "corrupt_file") from exc
    pages = doc.page_count
    for page in doc:
        text_parts.append(page.get_text("text"))
    text = "\n".join(text_parts).strip()
    used_ocr = False
    if len(text) < 80 and pages > 0:
        used_ocr = True
        ocr_text, ocr_warnings = _ocr_pdf(doc, pages)
        warnings.extend(ocr_warnings)
        if ocr_text.strip():
            text = ocr_text.strip()
        else:
            warnings.append(
                "This looks like a scanned resume and OCR was unavailable. "
                "Paste the text manually or upload a text-based PDF."
            )
    return ParsedDocument(text=text, pages=pages, used_ocr=used_ocr, warnings=warnings)


def _ocr_pdf(doc: object, pages: int) -> tuple[str, list[str]]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", ["OCR engine not installed (pytesseract/Pillow)"]
    chunks: list[str] = []
    warnings: list[str] = []
    for index in range(min(pages, 5)):
        try:
            page = doc[index]  # type: ignore[index]
            pixmap = page.get_pixmap(dpi=200)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            chunks.append(pytesseract.image_to_string(image))
        except Exception as exc:  # pragma: no cover - depends on tesseract binary
            warnings.append(f"OCR failed on page {index + 1}: {type(exc).__name__}")
            break
    return "\n".join(chunks), warnings


def _extract_docx(data: bytes) -> ParsedDocument:
    from docx import Document

    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise UploadError("Could not read the DOCX", "corrupt_file") from exc
    parts = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    text = "\n".join(parts)
    warnings = [] if text.strip() else ["No extractable text was found in this DOCX."]
    return ParsedDocument(text=text, pages=1, used_ocr=False, warnings=warnings)


def extract_text(ext: str, data: bytes) -> ParsedDocument:
    parsed = _extract_pdf(data) if ext == ".pdf" else _extract_docx(data)
    parsed.text = parsed.text[:60_000]
    if not parsed.text.strip():
        parsed.warnings.append("No text extracted; manual resume text entry is required.")
    return parsed
