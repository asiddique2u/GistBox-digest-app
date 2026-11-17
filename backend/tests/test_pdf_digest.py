import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pymupdf
from fastapi.testclient import TestClient

from main import app
from backend.app.agent.digest_models import DigestOutput
from app.services.pdf_digest import (
    MAX_PDF_BYTES,
    PDFPageLimitError,
    PDFProcessingError,
    PDFTooLargeError,
    UnsupportedPDFError,
    _copy_pdf,
    _extract_pdf,
    process_pdf_digest,
)
from app.services.request_context import DigestRequestContext

client = TestClient(app)


def make_pdf(page_count: int = 1, text: str | None = None) -> bytes:
    document = pymupdf.open()
    for _ in range(page_count):
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


class PDFDigestTests(unittest.TestCase):
    def test_extracts_selectable_text_and_metadata_title(self) -> None:
        text = (
            "This is selectable text from a PDF page, with enough characters "
            "to avoid invoking OCR during normal extraction."
        )
        document = pymupdf.open(stream=make_pdf(text=text), filetype="pdf")
        document.set_metadata({"title": "A PDF report"})

        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            path.write_bytes(document.tobytes())
            title, extracted = _extract_pdf(path, "uploaded.pdf")

        document.close()
        self.assertEqual(title, "A PDF report")
        self.assertIn("selectable text from a PDF page", extracted)

    def test_ocr_is_used_for_pages_without_selectable_text(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "scanned.pdf"
            path.write_bytes(make_pdf())
            with patch(
                "app.services.pdf_digest.pytesseract.image_to_string",
                return_value="Text recognized by OCR.",
            ) as image_to_string:
                title, extracted = _extract_pdf(path, "scanned.pdf")

        self.assertEqual(title, "scanned")
        self.assertEqual(extracted, "Text recognized by OCR.")
        image_to_string.assert_called_once()

    def test_rejects_documents_over_page_limit(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "long.pdf"
            path.write_bytes(make_pdf(page_count=21))
            with self.assertRaises(PDFPageLimitError):
                _extract_pdf(path, "long.pdf")

    def test_rejects_oversized_uploads(self) -> None:
        source = io.BytesIO(b"%PDF-" + (b"x" * MAX_PDF_BYTES))
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "large.pdf"
            with self.assertRaises(PDFTooLargeError):
                _copy_pdf(source, destination)

    def test_rejects_files_without_pdf_signature(self) -> None:
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "not-a-pdf.pdf"
            with self.assertRaises(UnsupportedPDFError):
                _copy_pdf(io.BytesIO(b"not a PDF"), destination)

    def test_temporary_upload_is_removed_when_extraction_fails(self) -> None:
        temporary_directory = None
        real_temporary_directory = TemporaryDirectory

        def capture_temporary_directory(prefix: str):
            nonlocal temporary_directory
            temporary_directory = real_temporary_directory(prefix=prefix)
            return temporary_directory

        context = DigestRequestContext(url="", detail_level="short")
        with (
            patch(
                "app.services.pdf_digest.TemporaryDirectory",
                side_effect=capture_temporary_directory,
            ),
            patch(
                "app.services.pdf_digest._extract_pdf",
                side_effect=PDFProcessingError("Unable to extract text."),
            ),
        ):
            with self.assertRaises(PDFProcessingError):
                process_pdf_digest(
                    io.BytesIO(make_pdf(text="Selectable text.")),
                    "report.pdf",
                    "short",
                    context,
                )

        self.assertIsNotNone(temporary_directory)
        self.assertFalse(Path(temporary_directory.name).exists())
        self.assertEqual(context.filename, "report.pdf")

    def test_temporary_upload_is_removed_after_digest_generation(self) -> None:
        temporary_directory = None
        real_temporary_directory = TemporaryDirectory

        def capture_temporary_directory(prefix: str):
            nonlocal temporary_directory
            temporary_directory = real_temporary_directory(prefix=prefix)
            return temporary_directory

        context = DigestRequestContext(url="", detail_level="short")
        digest = DigestOutput(title="A PDF digest", summary="- Main point.")

        def generate_digest(**kwargs):
            context.source_content = kwargs["text"]
            return digest

        with (
            patch(
                "app.services.pdf_digest.TemporaryDirectory",
                side_effect=capture_temporary_directory,
            ),
            patch(
                "app.services.pdf_digest.generate_digest_for_content",
                side_effect=generate_digest,
            ),
        ):
            result = process_pdf_digest(
                io.BytesIO(
                    make_pdf(
                        text=(
                            "This selectable PDF text is sufficiently long to "
                            "avoid OCR for the cleanup test."
                        )
                    )
                ),
                "report.pdf",
                "short",
                context,
            )

        self.assertEqual(result, digest)
        self.assertIsNotNone(temporary_directory)
        self.assertFalse(Path(temporary_directory.name).exists())
        self.assertIsNotNone(context.source_content)

    def test_pdf_endpoint_returns_filename_and_clears_request_context(self) -> None:
        digest = DigestOutput(title="A PDF digest", summary="- Main point.")

        def generate_digest(*, context: DigestRequestContext, **kwargs):
            context.filename = "report.pdf"
            context.source_content = "Temporary PDF text."
            return digest

        with patch("main.process_pdf_digest", side_effect=generate_digest) as process:
            response = client.post(
                "/digest/pdf",
                files={"file": ("report.pdf", make_pdf(), "application/pdf")},
                data={"detail_level": "medium"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "filename": "report.pdf",
                "detail_level": "medium",
                "title": "A PDF digest",
                "summary": "- Main point.",
            },
        )
        context = process.call_args.kwargs["context"]
        self.assertEqual(context.filename, None)
        self.assertIsNone(context.source_content)
        self.assertIsNone(context.request_id)

    def test_pdf_endpoint_rejects_invalid_detail_level(self) -> None:
        with patch("main.process_pdf_digest") as process:
            response = client.post(
                "/digest/pdf",
                files={"file": ("report.pdf", make_pdf(), "application/pdf")},
                data={"detail_level": "extra-long"},
            )

        self.assertEqual(response.status_code, 422)
        process.assert_not_called()

    def test_pdf_cors_allows_local_frontend_and_rejects_other_origins(self) -> None:
        allowed = client.options(
            "/digest/pdf",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        rejected = client.options(
            "/digest/pdf",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )
        self.assertNotIn("access-control-allow-origin", rejected.headers)


if __name__ == "__main__":
    unittest.main()
