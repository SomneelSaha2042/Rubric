import json
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import ApprovedRubric, RubricDraft, RubricSummary, RubricVersionSummary


class MissingRubricError(Exception):
    pass


class StaleRevisionError(Exception):
    pass


class RubricStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rubric_versions (
                    rubric_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    questions_json TEXT NOT NULL,
                    creation_source TEXT NOT NULL,
                    base_version INTEGER,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (rubric_id, version)
                )
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def approve(self, draft: RubricDraft) -> ApprovedRubric:
        rubric_id = draft.base_version.id if draft.base_version else str(uuid4())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = connection.execute(
                "SELECT MAX(version) FROM rubric_versions WHERE rubric_id = ?", (rubric_id,)
            ).fetchone()[0]
            if draft.base_version:
                if latest is None:
                    raise MissingRubricError
                if latest != draft.base_version.version:
                    raise StaleRevisionError
                version = latest + 1
            else:
                version = 1
            created_at = datetime.now(timezone.utc)
            connection.execute(
                """
                INSERT INTO rubric_versions
                    (rubric_id, version, role, questions_json, creation_source, base_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rubric_id,
                    version,
                    draft.role,
                    json.dumps([question.model_dump() for question in draft.questions]),
                    draft.creation_source,
                    draft.base_version.version if draft.base_version else None,
                    created_at.isoformat(),
                ),
            )
        return ApprovedRubric(
            id=rubric_id, version=version, created_at=created_at, **draft.model_dump()
        )

    def get(self, rubric_id: str, version: int) -> ApprovedRubric:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM rubric_versions WHERE rubric_id = ? AND version = ?",
                (rubric_id, version),
            ).fetchone()
        if row is None:
            raise MissingRubricError
        base_version = (
            {"id": rubric_id, "version": row["base_version"]}
            if row["base_version"] is not None
            else None
        )
        return ApprovedRubric(
            id=rubric_id,
            version=row["version"],
            role=row["role"],
            questions=json.loads(row["questions_json"]),
            creation_source=row["creation_source"],
            base_version=base_version,
            created_at=row["created_at"],
        )

    def list(self) -> list[RubricSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT rubric_id, version, role, created_at FROM rubric_versions "
                "ORDER BY created_at DESC"
            ).fetchall()
        grouped: dict[str, RubricSummary] = {}
        for row in rows:
            summary = grouped.setdefault(
                row["rubric_id"], RubricSummary(id=row["rubric_id"], role=row["role"], versions=[])
            )
            summary.versions.append(
                RubricVersionSummary(version=row["version"], created_at=row["created_at"])
            )
        return list(grouped.values())
