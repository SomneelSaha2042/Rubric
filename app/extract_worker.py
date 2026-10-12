import json
import sys
from io import BytesIO

from pypdf import PdfReader


def result() -> dict[str, str]:
    try:
        reader = PdfReader(BytesIO(sys.stdin.buffer.read()), strict=True)
        if reader.is_encrypted:
            return {"error": "encrypted_pdf"}
        if len(reader.pages) > 100:
            return {"error": "too_many_pages"}
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            return {"error": "no_pdf_text"}
        if len(text.encode("utf-8")) > 1_000_000:
            return {"error": "too_much_text"}
        return {"text": text}
    except Exception:
        return {"error": "invalid_pdf"}


if __name__ == "__main__":
    sys.stdout.write(json.dumps(result()))
