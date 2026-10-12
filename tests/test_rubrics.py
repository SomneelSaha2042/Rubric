import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


class RubricApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "rubric.sqlite3"
        self.client = TestClient(create_app(database))

    def tearDown(self) -> None:
        self.client.close()
        self.temp_dir.cleanup()

    def test_approve_and_retrieve_manual_rubric(self) -> None:
        draft = {
            "role": "Backend engineer",
            "creation_source": "manual",
            "questions": [
                {
                    "id": "backend_evidence",
                    "domain": "Backend development",
                    "type": "choice",
                    "instructions": "What backend evidence is documented?",
                    "criteria": {
                        "documented": "A project and contribution are described.",
                        "insufficient": "No contribution is documented.",
                    },
                }
            ],
        }

        approved = self.client.post("/api/rubrics", json=draft)

        self.assertEqual(201, approved.status_code, approved.text)
        body = approved.json()
        self.assertEqual(1, body["version"])
        self.assertEqual("Backend engineer", body["role"])
        self.assertEqual(draft["questions"], body["questions"])
        retrieved = self.client.get(
            f'/api/rubrics/{body["id"]}/versions/{body["version"]}'
        )
        self.assertEqual(200, retrieved.status_code, retrieved.text)
        self.assertEqual(body, retrieved.json())
        self.assertEqual("no-store", retrieved.headers["cache-control"])

    def test_invalid_questions_cannot_be_approved(self) -> None:
        invalid = {
            "role": "Backend engineer",
            "creation_source": "manual",
            "questions": [
                {
                    "id": "evidence",
                    "domain": "Backend",
                    "type": "score",
                    "instructions": "Rate the evidence.",
                    "criteria": ["Strong"],
                }
            ],
        }

        response = self.client.post("/api/rubrics", json=invalid)

        self.assertEqual(422, response.status_code)
        self.assertEqual("invalid_request", response.json()["detail"]["code"])
        self.assertNotIn("Strong", response.text)

    def test_revision_appends_version_and_rejects_stale_base(self) -> None:
        draft = {
            "role": "Backend engineer",
            "creation_source": "manual",
            "questions": [
                {
                    "id": "experience",
                    "domain": "Experience",
                    "type": "noul",
                    "instructions": "Does the resume document relevant experience?",
                }
            ],
        }
        first = self.client.post("/api/rubrics", json=draft).json()
        revision = {
            **draft,
            "role": "Senior backend engineer",
            "creation_source": "revision",
            "base_version": {"id": first["id"], "version": 1},
        }

        second_response = self.client.post("/api/rubrics", json=revision)
        stale_response = self.client.post("/api/rubrics", json=revision)

        self.assertEqual(201, second_response.status_code, second_response.text)
        second = second_response.json()
        self.assertEqual(2, second["version"])
        self.assertEqual("Senior backend engineer", second["role"])
        self.assertEqual(409, stale_response.status_code)
        listing = self.client.get("/api/rubrics").json()
        self.assertEqual([2, 1], [item["version"] for item in listing[0]["versions"]])
        original = self.client.get(f'/api/rubrics/{first["id"]}/versions/1').json()
        self.assertEqual("Backend engineer", original["role"])


if __name__ == "__main__":
    unittest.main()
