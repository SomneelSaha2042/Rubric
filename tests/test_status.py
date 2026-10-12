import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


class StatusApiTests(unittest.TestCase):
    def test_reports_readiness_without_exposing_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "DRAFTING_URL": "https://example.test/chat",
            "DRAFTING_MODEL": "draft-model",
            "DRAFTING_API_KEY": "draft-secret",
            "JEV_API_KEY": "jev-secret",
            "LAYA_URL": "https://example.test/systemone",
            "LAYA_API_KEY": "laya-secret",
            "LAYA_MODEL": "laya",
        }, clear=False):
            with TestClient(create_app(Path(directory) / "rubric.sqlite3")) as client:
                response = client.get("/api/status")

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["drafting"]["configured"])
        self.assertTrue(response.json()["providers"]["jev"]["configured"])
        self.assertTrue(response.json()["providers"]["laya"]["configured"])
        self.assertNotIn("secret", response.text)


if __name__ == "__main__":
    unittest.main()
