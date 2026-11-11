import unittest
import uuid

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import PopupVersion


class FakeDatabase:
    def __init__(self) -> None:
        self.version = None
        self.website_url = "https://store.example/"

    def scalar(self, query):
        if "websites.url" in str(query):
            return self.website_url
        return self.version


class PublicWidgetAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDatabase()
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_published_config_returns_only_widget_fields(self) -> None:
        campaign_id = uuid.uuid4()
        version_id = uuid.uuid4()
        config = {"headline": "A thoughtful hello", "theme": {"accent_color": "#35694A"}}
        self.db.version = PopupVersion(
            id=version_id,
            campaign_id=campaign_id,
            config_json=config,
            label="A",
            created_by="user",
        )

        response = self.client.get(f"/api/public/campaigns/{campaign_id}/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "campaign_id": str(campaign_id),
                "version_id": str(version_id),
                "config": config,
            },
        )

    def test_missing_published_default_returns_404(self) -> None:
        response = self.client.get(f"/api/public/campaigns/{uuid.uuid4()}/config")
        self.assertEqual(response.status_code, 404)

    def test_config_allows_only_the_analyzed_website_origin(self) -> None:
        campaign_id = uuid.uuid4()
        self.db.version = PopupVersion(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            config_json={"headline": "Hello"},
            label="A",
            created_by="user",
        )
        allowed = self.client.get(
            f"/api/public/campaigns/{campaign_id}/config",
            headers={"Origin": "https://store.example"},
        )
        denied = self.client.get(
            f"/api/public/campaigns/{campaign_id}/config",
            headers={"Origin": "https://unrelated.example"},
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers["access-control-allow-origin"], "https://store.example"
        )
        self.assertEqual(denied.status_code, 403)

    def test_widget_script_is_served_as_javascript(self) -> None:
        response = self.client.get("/widget.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers["content-type"])
        self.assertIn("attachShadow", response.text)


if __name__ == "__main__":
    unittest.main()