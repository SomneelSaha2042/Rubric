import math
import time
from typing import Protocol

import httpx

from .models import ChoiceQuestion, NoulQuestion, Question, ScoreQuestion


class Evaluator(Protocol):
    async def evaluate(self, state: str, questions: list[Question]) -> dict: ...


def _probability(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("invalid probability")
    return float(value)


def _distribution(value: object, labels: set[str], tolerance: float) -> None:
    if not isinstance(value, dict) or set(value) != labels:
        raise ValueError("invalid distribution labels")
    total = sum(_probability(item) for item in value.values())
    if abs(total - 1) > tolerance:
        raise ValueError("invalid distribution total")


def validate_answers(data: object, questions: list[Question], tolerance: float) -> dict:
    if not isinstance(data, dict) or set(data) != {question.id for question in questions}:
        raise ValueError("answer IDs do not match")
    for question in questions:
        answer = data[question.id]
        if not isinstance(answer, dict) or answer.get("type") != question.type:
            raise ValueError("answer type does not match")
        if isinstance(question, NoulQuestion):
            _probability(answer.get("noul"))
        elif isinstance(question, ChoiceQuestion):
            labels = set(question.criteria)
            if answer.get("choice") not in labels:
                raise ValueError("choice label does not match")
            _probability(answer.get("confidence"))
            _distribution(answer.get("probabilities"), labels, tolerance)
        elif isinstance(question, ScoreQuestion):
            score = answer.get("score")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= len(question.criteria) - 1:
                raise ValueError("score is outside its range")
            _probability(answer.get("confidence"))
            labels = {str(index) for index in range(len(question.criteria))}
            if answer.get("legend") != {str(index): level for index, level in enumerate(question.criteria)}:
                raise ValueError("score legend does not match")
            _distribution(answer.get("probabilities"), labels, tolerance)
        if "answer_confidence" in answer:
            _probability(answer["answer_confidence"])
        action = answer.get("action")
        if isinstance(action, dict) and "act_probability" in action:
            _probability(action["act_probability"])
    return data


class SystemOneEvaluator:
    def __init__(
        self,
        backend: str,
        url: str,
        api_key: str,
        model: str,
        *,
        max_len: int | None = None,
        tolerance: float = 1e-5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.backend = backend
        self.url = url
        self.api_key = api_key
        self.model = model
        self.max_len = max_len
        self.tolerance = tolerance
        self.client = client

    def _error(self, started: float, code: str, message: str) -> dict:
        return {
            "status": "error",
            "backend": self.backend,
            "model": self.model,
            "error": {"code": code, "message": message},
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }

    async def evaluate(self, state: str, questions: list[Question]) -> dict:
        started = time.monotonic()
        if not self.url or not self.api_key or not self.model:
            return self._error(started, "not_configured", f"{self.backend.title()} is not configured.")
        payload = {
            "model": self.model,
            "state": state,
            "questions": {
                question.id: question.model_dump(exclude={"id", "domain"}, exclude_none=True)
                for question in questions
            },
        }
        if self.max_len is not None:
            payload["max_len"] = self.max_len

        client = self.client or httpx.AsyncClient(timeout=30, follow_redirects=False)
        try:
            response = await client.post(
                self.url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if not response.is_success:
                return self._error(started, "provider_error", f"{self.backend.title()} returned HTTP {response.status_code}.")
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("response is not an object")
            answers = validate_answers(body.get("answers"), questions, self.tolerance)
            outcome = {
                "status": "ok",
                "backend": self.backend,
                "model": self.model,
                "served_model": body.get("model"),
                "answers": answers,
                "elapsed_ms": round((time.monotonic() - started) * 1000),
            }
            if isinstance(body.get("usage"), dict):
                outcome["usage"] = body["usage"]
            return outcome
        except httpx.TimeoutException:
            return self._error(started, "timeout", f"{self.backend.title()} timed out.")
        except httpx.RequestError:
            return self._error(started, "unavailable", f"{self.backend.title()} could not be reached.")
        except (ValueError, TypeError, KeyError):
            return self._error(started, "invalid_response", f"{self.backend.title()} returned an invalid response.")
        finally:
            if self.client is None:
                await client.aclose()
