import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.drafting import DraftError, OpenAIJsonDrafter
from app.main import create_app
from app.models import RubricDraft


class FakeDrafter:
    async def draft(self, role: str, _job_description: str) -> RubricDraft:
        return RubricDraft.model_validate({
            "role": role,
            "creation_source": "assisted",
            "questions": [{
                "id": "backend_evidence",
                "domain": "Backend development",
                "type": "choice",
                "instructions": "What backend evidence is documented?",
                "criteria": {"documented": "A contribution is described.", "missing": "No contribution is described."},
            }],
        })


class DraftingApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "rubric.sqlite3"
        self.client = TestClient(create_app(self.database, drafter=FakeDrafter()))

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_returns_validated_unapproved_draft_without_storing_job_description(self) -> None:
        response = self.client.post("/api/rubrics/draft", json={"role": "Backend engineer", "job_description": "Synthetic private job description"})

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("assisted", response.json()["creation_source"])
        self.assertEqual([], self.client.get("/api/rubrics").json())
        self.assertNotIn(b"Synthetic private job description", self.database.read_bytes())


class DraftingAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_json_that_does_not_match_the_rubric_schema(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": [{"message": {"content": '{"questions":[{"type":"score"}]}'}}]})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        drafter = OpenAIJsonDrafter("https://example.test/chat/completions", "model", "key", client=client)

        with self.assertRaises(DraftError) as raised:
            await drafter.draft("Engineer", "A synthetic job description")

        self.assertEqual("invalid_draft", raised.exception.code)
        await client.aclose()

    async def test_reports_missing_configuration_without_a_provider_call(self) -> None:
        drafter = OpenAIJsonDrafter("", "", "")

        with self.assertRaises(DraftError) as raised:
            await drafter.draft("Engineer", "A synthetic job description")

        self.assertEqual(503, raised.exception.status)


if __name__ == "__main__":
    unittest.main()
