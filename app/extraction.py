import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import Request
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header


MAX_PDF_BYTES = 10_000_000
MAX_MULTIPART_BYTES = MAX_PDF_BYTES + 65_536


class UploadError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


@dataclass
class UploadState:
    data: bytearray = field(default_factory=bytearray)
    header_name: bytearray = field(default_factory=bytearray)
    header_value: bytearray = field(default_factory=bytearray)
    headers: dict[bytes, bytes] = field(default_factory=dict)
    accepting: bool = False
    files: int = 0

    def part_begin(self) -> None:
        self.headers = {}
        self.accepting = False

    def header_field(self, data: bytes, start: int, end: int) -> None:
        self.header_name.extend(data[start:end])

    def header_value_data(self, data: bytes, start: int, end: int) -> None:
        self.header_value.extend(data[start:end])

    def header_end(self) -> None:
        self.headers[bytes(self.header_name).lower()] = bytes(self.header_value)
        self.header_name.clear()
        self.header_value.clear()

    def headers_finished(self) -> None:
        _kind, options = parse_options_header(self.headers.get(b"content-disposition"))
        if options.get(b"name") != b"file" or b"filename" not in options:
            raise UploadError(422, "invalid_upload", "Upload one PDF in the file field.")
        if self.files:
            raise UploadError(422, "invalid_upload", "Upload only one PDF.")
        media_type, _options = parse_options_header(self.headers.get(b"content-type"))
        if media_type != b"application/pdf":
            raise UploadError(422, "invalid_upload", "The file must be a PDF.")
        self.files += 1
        self.accepting = True

    def part_data(self, data: bytes, start: int, end: int) -> None:
        if not self.accepting:
            return
        if len(self.data) + end - start > MAX_PDF_BYTES:
            raise UploadError(413, "pdf_too_large", "The PDF must be 10 MB or smaller.")
        self.data.extend(data[start:end])


async def read_pdf_upload(request: Request) -> bytes:
    media_type, options = parse_options_header(request.headers.get("content-type"))
    boundary = options.get(b"boundary")
    if media_type != b"multipart/form-data" or not boundary:
        raise UploadError(422, "invalid_upload", "Upload one PDF in the file field.")

    state = UploadState()
    parser = MultipartParser(
        boundary,
        {
            "on_part_begin": state.part_begin,
            "on_header_field": state.header_field,
            "on_header_value": state.header_value_data,
            "on_header_end": state.header_end,
            "on_headers_finished": state.headers_finished,
            "on_part_data": state.part_data,
        },
        max_size=MAX_MULTIPART_BYTES,
    )
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_MULTIPART_BYTES:
            raise UploadError(413, "pdf_too_large", "The PDF must be 10 MB or smaller.")
        parser.write(chunk)
    parser.finalize()
    if state.files != 1 or not state.data:
        raise UploadError(422, "invalid_upload", "Upload one nonempty PDF in the file field.")
    if not state.data.startswith(b"%PDF-"):
        raise UploadError(422, "invalid_pdf", "The uploaded file is not a readable PDF.")
    return bytes(state.data)


def extract_pdf(pdf: bytes) -> dict[str, str]:
    worker = Path(__file__).with_name("extract_worker.py")
    try:
        completed = subprocess.run(
            [sys.executable, str(worker)],
            input=pdf,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"error": "pdf_timeout"}
    try:
        value = json.loads(completed.stdout)
        return value if isinstance(value, dict) else {"error": "invalid_pdf"}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"error": "invalid_pdf"}
