import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .models import ApprovedRubric, RubricDraft, RubricSummary
from .store import MissingRubricError, RubricStore, StaleRevisionError


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message}})


def create_app(database: Path | None = None) -> FastAPI:
    store = RubricStore(database or Path(os.getenv("SQLITE_PATH", "data/rubric.sqlite3")))
    app = FastAPI(title="Rubric")

    @app.middleware("http")
    async def no_store(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = [".".join(str(part) for part in item["loc"] if part != "body") for item in exc.errors()]
        response = error(422, "invalid_request", "The request is invalid.")
        response.body = JSONResponse(
            status_code=422,
            content={"detail": {"code": "invalid_request", "message": "The request is invalid.", "fields": fields}},
        ).body
        return response

    @app.post("/api/rubrics", response_model=ApprovedRubric, status_code=201)
    def approve_rubric(draft: RubricDraft):
        try:
            return store.approve(draft)
        except MissingRubricError:
            return error(404, "rubric_not_found", "The base rubric version was not found.")
        except StaleRevisionError:
            return error(409, "stale_revision", "A newer rubric version already exists.")

    @app.get("/api/rubrics", response_model=list[RubricSummary])
    def list_rubrics():
        return store.list()

    @app.get("/api/rubrics/{rubric_id}/versions/{version}", response_model=ApprovedRubric)
    def get_rubric(rubric_id: str, version: int):
        try:
            return store.get(rubric_id, version)
        except MissingRubricError:
            return error(404, "rubric_not_found", "The rubric version was not found.")

    return app


app = create_app()
