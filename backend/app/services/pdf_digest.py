from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

import pymupdf
import pytesseract
from PIL import Image

from ..agent.digest_models import DigestDetailLevel, DigestOutput
from .content_digest import generate_digest_for_content
from .request_context import DigestRequestContext

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 20
MAX_REQUEST_BODY_BYTES = MAX_PDF_BYTES + 64 * 1024
UPLOAD_CHUNK_BYTES = 64 * 1024
MAX_OCR_IMAGE_DIMENSION = 3000
OCR_DPI = 150
OCR_TIMEOUT_SECONDS = 20
MIN_EMBEDDED_TEXT_CHARS = 50


class UnsupportedPDFError(ValueError):
    pass


class PDFTooLargeError(ValueError):
    pass


class PDFPageLimitError(ValueError):
    pass


class PDFProcessingError(RuntimeError):
    pass


class OCRUnavailableError(RuntimeError):
    pass


class OCRProcessingError(RuntimeError):
    pass


def _safe_filename(filename: str) -> str:
    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not safe_name.lower().endswith(".pdf"):
        raise UnsupportedPDFError("Upload a PDF file.")
    return safe_name[:255]


def _copy_pdf(source: BinaryIO, destination: Path) -> None:
    source.seek(0)
    size = 0
    header = bytearray()

    with destination.open("wb") as target:
        while chunk := source.read(UPLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                raise PDFTooLargeError("The PDF exceeds the 10 MB limit.")
            if len(header) < 1024:
                header.extend(chunk[: 1024 - len(header)])
            target.write(chunk)

    if b"%PDF-" not in header:
        raise UnsupportedPDFError("The uploaded file is not a valid PDF.")


def _ocr_page(page: pymupdf.Page) -> str:
    width = page.rect.width
    height = page.rect.height
    largest_dimension = max(width, height)
    if largest_dimension <= 0:
        raise PDFProcessingError("A PDF page has invalid dimensions.")

    scale = min(OCR_DPI / 72, MAX_OCR_IMAGE_DIMENSION / largest_dimension)
    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(scale, scale),
        colorspace=pymupdf.csRGB,
        alpha=False,
    )
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    try:
        return pytesseract.image_to_string(
            image,
            lang="eng",
            timeout=OCR_TIMEOUT_SECONDS,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRUnavailableError(
            "Scanned PDFs cannot be processed because OCR is unavailable."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise OCRProcessingError("OCR could not read a page in this PDF.") from exc
    except RuntimeError as exc:
        raise OCRProcessingError("OCR timed out while processing this PDF.") from exc
    finally:
        image.close()


def _extract_pdf(path: Path, filename: str) -> tuple[str, str]:
    try:
        document = pymupdf.open(str(path))
    except (
        pymupdf.FileDataError,
        pymupdf.EmptyFileError,
        ValueError,
        RuntimeError,
    ) as exc:
        raise UnsupportedPDFError("The uploaded file is not a readable PDF.") from exc

    with document:
        if document.needs_pass:
            raise PDFProcessingError("Password-protected PDFs are not supported.")
        try:
            page_count = document.page_count
        except (pymupdf.FileDataError, ValueError, RuntimeError) as exc:
            raise PDFProcessingError("The PDF page data could not be read.") from exc
        if page_count == 0:
            raise PDFProcessingError("The PDF has no pages.")
        if page_count > MAX_PDF_PAGES:
            raise PDFPageLimitError(
                f"The PDF exceeds the {MAX_PDF_PAGES}-page limit."
            )

        page_texts: list[str] = []
        try:
            for page in document:
                text = page.get_text()
                if len(text.strip()) < MIN_EMBEDDED_TEXT_CHARS:
                    ocr_text = _ocr_page(page)
                    if ocr_text.strip():
                        text = ocr_text
                page_texts.append(text.strip())
        except (OCRUnavailableError, OCRProcessingError):
            raise
        except (pymupdf.FileDataError, ValueError, RuntimeError) as exc:
            raise PDFProcessingError("The PDF could not be fully processed.") from exc

        full_text = "\n\n".join(text for text in page_texts if text)
        if not full_text:
            raise PDFProcessingError(
                "No readable text was found in the PDF, including with OCR."
            )

        metadata_title = ((document.metadata or {}).get("title") or "").strip()
        title = metadata_title or Path(filename).stem or "Uploaded PDF"
        return title[:120], full_text


def process_pdf_digest(
    source: BinaryIO,
    filename: str,
    detail_level: DigestDetailLevel,
    context: DigestRequestContext,
) -> DigestOutput:
    safe_filename = _safe_filename(filename)
    context.source_type = "pdf"
    context.filename = safe_filename

    with TemporaryDirectory(prefix="gistbox-pdf-") as directory:
        pdf_path = Path(directory) / "upload.pdf"
        _copy_pdf(source, pdf_path)
        title, text = _extract_pdf(pdf_path, safe_filename)

    context.detail_level = detail_level
    return generate_digest_for_content(
        context=context,
        title=title,
        text=text,
        article_type="pdf",
    )
