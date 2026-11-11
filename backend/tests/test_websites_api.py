import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import User
from app.services.website_analyzer import WebsiteData
from app.services.url_safety import UnsafeURLError


class FakeDatabase:
    def __init__(self) -> None:
        self.website = None

    def scalar(self, _query):
        return self.website

    def add(self, website) -> None:
        website.id = uuid.uuid4()
        self.website = website

    def commit(self) -> None:
        pass

    def refresh(self, _website) -> None:
        pass


class WebsitesAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDatabase()
        self.user = User(
            id=uuid.uuid4(),
            email="owner@example.com",
            password_hash="not-used-in-this-test",
        )
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_analysis_is_saved_and_returned(self) -> None:
        site = WebsiteData(
            url="https://store.example/",
            title="Northstar",
            meta_description="Outdoor clothing",
            headings=["Jackets"],
            visible_text="Jackets and shirts",
            links=[],
            image_candidates=[],
            logo_candidates=[],
            brand_colors=["#174A38"],
            promotions=[],
        )
        generated = {
            "business_type": "Outdoor apparel store",
            "target_audience": "Outdoor customers",
            "brand_tone": "Practical",
            "products": ["Jackets"],
            "brand_colors": ["#174A38"],
            "suggested_offer": {
                "text": "Explore the new collection",
                "requires_owner_approval": True,
            },
        }

        with (
            patch(
                "app.api.websites.analyze_website", new=AsyncMock(return_value=site)
            ),
            patch(
                "app.api.websites.generate_website_analysis",
                new=AsyncMock(return_value=__import__(
                    "app.schemas.website", fromlist=["WebsiteAnalysis"]
                ).WebsiteAnalysis.model_validate(generated)),
            ),
        ):
            response = self.client.post(
                "/api/websites/analyze", json={"url": "https://store.example/"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"]["business_type"], "Outdoor apparel store")
        self.assertEqual(self.db.website.url, "https://store.example/")
        self.assertTrue(self.db.website.analysis_json["suggested_offer"]["requires_owner_approval"])
        self.assertIsNotNone(self.db.website.analyzed_at)

    def test_invalid_url_is_rejected_by_request_schema(self) -> None:
        response = self.client.post("/api/websites/analyze", json={"url": "file:///etc/passwd"})
        self.assertEqual(response.status_code, 422)

    def test_ssrf_rejection_is_returned_as_client_error(self) -> None:
        with patch(
            "app.api.websites.analyze_website",
            new=AsyncMock(side_effect=UnsafeURLError("Hostname resolves to a non-public IP address")),
        ):
            response = self.client.post(
                "/api/websites/analyze", json={"url": "http://127.0.0.1/admin"}
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("non-public", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()