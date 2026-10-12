import json
from typing import Protocol

import httpx
from pydantic import ValidationError

from .models import RubricDraft


class DraftError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


class Drafter(Protocol):
    async def draft(self, role: str, job_description: str) -> RubricDraft: ...


class OpenAIJsonDrafter:
    def __init__(self, url: str, model: str, api_key: str, *, client: httpx.AsyncClient | None = None) -> None:
        self.url = url
        self.model = model
        self.api_key = api_key
        self.client = client

    async def draft(self, role: str, job_description: str) -> RubricDraft:
        if not self.url or not self.model or not self.api_key:
            raise DraftError(503, "drafting_not_configured", "Assisted drafting is not configured. Use manual mode or configure the drafting endpoint.")
        prompt = """Return JSON with exactly one key, questions. questions is a nonempty array of resume-evidence questions. Every question has a stable snake_case id, domain, instructions, type, and criteria when required. type is choice, score, or noul. choice criteria maps 2-255 labels to descriptions. score criteria is 2-10 ordered descriptive levels. noul instructions state an explicit proposition and may have criteria with exactly false and true descriptions. Ask only about documented evidence; do not infer protected traits or overall candidate rank."""
        client = self.client or httpx.AsyncClient(timeout=30, follow_redirects=False)
        try:
            response = await client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Role: {role}\n\nJob description:\n{job_description}"},
                    ],
                },
            )
            if not response.is_success:
                raise DraftError(502, "draft_provider_error", f"The drafting provider returned HTTP {response.status_code}.")
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            value = json.loads(content)
            if not isinstance(value, dict) or set(value) != {"questions"}:
                raise ValueError
            return RubricDraft.model_validate({"role": role, "creation_source": "assisted", "questions": value["questions"]})
        except DraftError:
            raise
        except httpx.TimeoutException as exc:
            raise DraftError(504, "draft_timeout", "The drafting provider timed out.") from exc
        except httpx.RequestError as exc:
            raise DraftError(502, "draft_unavailable", "The drafting provider could not be reached.") from exc
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError, KeyError, IndexError) as exc:
            raise DraftError(502, "invalid_draft", "The drafting provider returned an incomplete or invalid rubric. Try again or use manual mode.") from exc
        finally:
            if self.client is None:
                await client.aclose()
