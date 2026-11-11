import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.auth import get_current_user
from app.main import app
from app.models import User
from app.schemas.popup import PopupVariants
from backend.tests.test_popup_generator import sample_analysis, variants_json


class PopupsAPITests(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: User(
            id=uuid.uuid4(),
            email="owner@example.com",
            password_hash="not-used-in-this-test",
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_generate_endpoint_returns_three_valid_variants(self) -> None:
        generated = PopupVariants.model_validate_json(variants_json())
        with patch(
            "app.api.popups.generate_popup_variants",
            new=AsyncMock(return_value=generated),
        ):
            response = self.client.post(
                "/api/popups/generate",
                json={"analysis": sample_analysis().model_dump(mode="json")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["variants"]), 3)
        self.assertEqual(
            {item["tone"] for item in response.json()["variants"]},
            {"friendly", "minimal", "bold"},
        )

    def test_generate_endpoint_requires_authentication(self) -> None:
        app.dependency_overrides.clear()
        response = self.client.post(
            "/api/popups/generate",
            json={"analysis": sample_analysis().model_dump(mode="json")},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()