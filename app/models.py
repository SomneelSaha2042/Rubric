from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QuestionBase(Model):
    id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    instructions: str = Field(min_length=1)


class ChoiceQuestion(QuestionBase):
    type: Literal["choice"]
    criteria: dict[str, str]

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value: dict[str, str]) -> dict[str, str]:
        if not 2 <= len(value) <= 255:
            raise ValueError("choice criteria must contain 2 to 255 options")
        if any(not key.strip() or not description.strip() for key, description in value.items()):
            raise ValueError("choice labels and descriptions must be nonempty")
        return value


class ScoreQuestion(QuestionBase):
    type: Literal["score"]
    criteria: list[str]

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value: list[str]) -> list[str]:
        cleaned = [level.strip() for level in value]
        if not 2 <= len(cleaned) <= 10:
            raise ValueError("score criteria must contain 2 to 10 levels")
        if any(not level for level in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("score levels must be nonempty and distinct")
        return cleaned


class NoulQuestion(QuestionBase):
    type: Literal["noul"]
    criteria: dict[str, str] | None = None

    @field_validator("criteria")
    @classmethod
    def validate_criteria(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is not None and (
            set(value) != {"false", "true"} or any(not item.strip() for item in value.values())
        ):
            raise ValueError("noul criteria must define nonempty false and true descriptions")
        return value


Question = Annotated[ChoiceQuestion | ScoreQuestion | NoulQuestion, Field(discriminator="type")]


class RubricRef(Model):
    id: str = Field(min_length=1)
    version: int = Field(ge=1)


class RubricDraft(Model):
    role: str = Field(min_length=1)
    creation_source: Literal["manual", "assisted", "revision"]
    questions: list[Question] = Field(min_length=1)
    base_version: RubricRef | None = None

    @model_validator(mode="after")
    def validate_draft(self) -> "RubricDraft":
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique")
        if (self.creation_source == "revision") != (self.base_version is not None):
            raise ValueError("only revisions require a base version")
        return self


class ApprovedRubric(RubricDraft):
    id: str
    version: int
    created_at: datetime


class RubricVersionSummary(Model):
    version: int
    created_at: datetime


class RubricSummary(Model):
    id: str
    role: str
    versions: list[RubricVersionSummary]


class EvaluationRequest(Model):
    rubric: RubricRef
    reviewed_text: str = Field(min_length=1, max_length=1_000_000)
