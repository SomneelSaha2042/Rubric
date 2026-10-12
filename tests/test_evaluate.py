import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.evaluation import SystemOneEvaluator
from app.main import create_app
from app.models import ChoiceQuestion


class FakeEvaluator:
    def __init__(self, outcome: dict):
        self.outcome = outcome

    async def evaluate(self, _state: str, _questions: list) -> dict:
        return self.outcome


class EvaluationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "rubric.sqlite3"
        evaluators = {
            "jev": FakeEvaluator({"status": "error", "backend": "jev", "model": "jev-1.13.0", "error": {"code": "timeout", "message": "Jev timed out."}, "elapsed_ms": 20}),
            "laya": FakeEvaluator({"status": "ok", "backend": "boundless", "model": "convaiinnovations/laya", "answers": {"evidence": {"type": "noul", "noul": 0.8}}, "elapsed_ms": 12}),
        }
        self.client = TestClient(create_app(self.database, evaluators=evaluators))
        approved = self.client.post("/api/rubrics", json={
            "role": "Engineer",
            "creation_source": "manual",
            "questions": [{"id": "evidence", "domain": "Experience", "type": "noul", "instructions": "Is relevant experience documented?"}],
        }).json()
        self.reference = {"id": approved["id"], "version": approved["version"]}

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_preserves_success_when_other_provider_fails(self) -> None:
        response = self.client.post("/api/evaluate", json={"rubric": self.reference, "reviewed_text": "Synthetic candidate evidence"})

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("error", response.json()["jev"]["status"])
        self.assertEqual(0.8, response.json()["laya"]["answers"]["evidence"]["noul"])
        self.assertNotIn(b"Synthetic candidate evidence", self.database.read_bytes())

    def test_requires_an_approved_rubric_version(self) -> None:
        response = self.client.post("/api/evaluate", json={"rubric": {"id": "missing", "version": 1}, "reviewed_text": "Synthetic text"})

        self.assertEqual(404, response.status_code)
        self.assertEqual("rubric_not_found", response.json()["detail"]["code"])


class SystemOneAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_questions_and_validates_provider_answers(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = __import__("json").loads(request.content)
            self.assertEqual("Synthetic state", payload["state"])
            self.assertEqual(8192, payload["max_len"])
            self.assertEqual({"type", "instructions", "criteria"}, set(payload["questions"]["evidence"]))
            return httpx.Response(200, json={
                "model": "convaiinnovations/laya",
                "answers": {"evidence": {"type": "choice", "choice": "yes", "confidence": 0.7, "probabilities": {"yes": 0.8, "no": 0.2}}},
                "usage": {"input_tokens": 10, "output_tokens": 0},
            })

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        evaluator = SystemOneEvaluator("boundless", "https://example.test/systemone", "key", "convaiinnovations/laya", max_len=8192, tolerance=0.00011, client=client)
        question = ChoiceQuestion(id="evidence", domain="Experience", instructions="What is documented?", type="choice", criteria={"yes": "Evidence exists", "no": "No evidence"})

        outcome = await evaluator.evaluate("Synthetic state", [question])

        self.assertEqual("ok", outcome["status"])
        self.assertEqual(10, outcome["usage"]["input_tokens"])
        await client.aclose()

    async def test_rejects_malformed_provider_answers(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"answers": {"wrong_id": {"type": "choice", "choice": "yes", "confidence": 1, "probabilities": {"yes": 1, "no": 0}}}})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        evaluator = SystemOneEvaluator("boundless", "https://example.test/systemone", "key", "laya", max_len=8192, client=client)
        question = ChoiceQuestion(id="evidence", domain="Experience", instructions="What is documented?", type="choice", criteria={"yes": "Evidence exists", "no": "No evidence"})

        outcome = await evaluator.evaluate("Synthetic state", [question])

        self.assertEqual("error", outcome["status"])
        self.assertEqual("invalid_response", outcome["error"]["code"])
        await client.aclose()


if __name__ == "__main__":
    unittest.main()
