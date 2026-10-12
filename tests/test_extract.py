import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import create_app


def text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(
        DictionaryObject(
            {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    content = DecodedStreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(content)
    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output.read()


class ExtractApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "rubric.sqlite3"
        self.client = TestClient(create_app(database))

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_extracts_text_pdf_without_retaining_candidate_data(self) -> None:
        response = self.client.post(
            "/api/extract",
            files={"file": ("resume.pdf", text_pdf("Synthetic resume evidence"), "application/pdf")},
        )

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("Synthetic resume evidence", response.json()["text"].strip())
        database_bytes = (Path(self.temp_dir.name) / "rubric.sqlite3").read_bytes()
        self.assertNotIn(b"Synthetic resume evidence", database_bytes)

    def test_rejects_empty_or_non_pdf_uploads(self) -> None:
        blank = PdfWriter()
        blank.add_blank_page(width=612, height=792)
        output = BytesIO()
        blank.write(output)
        output.seek(0)

        empty = self.client.post(
            "/api/extract",
            files={"file": ("blank.pdf", output.read(), "application/pdf")},
        )
        invalid = self.client.post(
            "/api/extract",
            files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
        )

        self.assertEqual(422, empty.status_code)
        self.assertEqual("no_pdf_text", empty.json()["detail"]["code"])
        self.assertEqual(422, invalid.status_code)
        self.assertEqual("invalid_pdf", invalid.json()["detail"]["code"])

    def test_rejects_upload_over_ten_megabytes(self) -> None:
        response = self.client.post(
            "/api/extract",
            files={"file": ("resume.pdf", b"%PDF-1.7\n" + b"x" * 10_000_000, "application/pdf")},
        )

        self.assertEqual(413, response.status_code)
        self.assertEqual("pdf_too_large", response.json()["detail"]["code"])


if __name__ == "__main__":
    unittest.main()
