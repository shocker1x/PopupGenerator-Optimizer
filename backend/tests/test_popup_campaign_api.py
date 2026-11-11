import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Campaign, PopupVersion, User, Website
from app.schemas.popup import PopupConfig
from backend.tests.test_popup_generator import sample_analysis, variant


class FakeDatabase:
    def __init__(self) -> None:
        self.current_user_id = None
        self.website = None
        self.campaign = None
        self.version = None
        self.added = []

    def scalar(self, query):
        statement = str(query)
        if "popup_versions.id" in statement and "websites.user_id" in statement:
            return self.version
        if "campaigns.id" in statement and "websites.user_id" in statement:
            return self.campaign
        if "popup_versions.id" in statement and "campaign_id" in statement:
            return self.version
        if "websites.id" in statement and "websites.user_id" in statement:
            return self.website
        return None

    def add(self, item) -> None:
        self.added.append(item)
        if isinstance(item, Campaign):
            item.id = uuid.uuid4()
            self.campaign = item
        elif isinstance(item, PopupVersion):
            item.id = uuid.uuid4()
            self.version = item

    def add_all(self, items) -> None:
        for item in items:
            self.add(item)

    def flush(self) -> None:
        if self.campaign and self.campaign.id is None:
            self.campaign.id = uuid.uuid4()

    def commit(self) -> None:
        pass

    def refresh(self, _item) -> None:
        pass


class PopupCampaignAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDatabase()
        self.user = User(
            id=uuid.uuid4(), email="owner@example.com", password_hash="unused"
        )
        self.website = Website(
            id=uuid.uuid4(), user_id=self.user.id, url="https://store.example/"
        )
        self.db.website = self.website
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_create_campaign_rejects_website_not_owned(self) -> None:
        self.db.website = None
        response = self.client.post(
            "/api/popups/campaigns",
            json={
                "website_id": str(uuid.uuid4()),
                "name": "Store popup",
                "variants": [variant("A", "friendly"), variant("B", "minimal"), variant("C", "bold")],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_campaign_persists_three_variants(self) -> None:
        response = self.client.post(
            "/api/popups/campaigns",
            json={
                "website_id": str(self.website.id),
                "name": "Northstar popup",
                "variants": [
                    variant("A", "friendly"),
                    variant("B", "minimal"),
                    variant("C", "bold"),
                ],
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "draft")
        self.assertEqual(len(response.json()["versions"]), 3)

    def test_update_preserves_protected_fields_from_stored_version(self) -> None:
        config = variant(
            "A", "friendly", {"text": "Owner-approved offer", "requires_owner_approval": True}
        )["config"]
        self.db.version = PopupVersion(
            id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            config_json=config,
            label="A",
            created_by="ai",
        )
        edited = {**config, "headline": "A clearer headline", "offer": None,
                  "consent_text": "Changed by the client", "email_placeholder": "Changed",
                  "layout": "compact"}
        response = self.client.patch(
            f"/api/popups/versions/{self.db.version.id}",
            json={"config": edited},
        )
        self.assertEqual(response.status_code, 200)
        saved = response.json()["config"]
        self.assertEqual(saved["headline"], "A clearer headline")
        self.assertEqual(saved["offer"], config["offer"])
        self.assertEqual(saved["consent_text"], config["consent_text"])
        self.assertEqual(saved["email_placeholder"], config["email_placeholder"])
        self.assertEqual(saved["layout"], config["layout"])

    def test_publishing_rejects_version_from_another_campaign(self) -> None:
        self.db.campaign = Campaign(
            id=uuid.uuid4(),
            website_id=self.website.id,
            name="Owned campaign",
            status="draft",
        )
        self.db.version = None
        response = self.client.post(
            f"/api/popups/campaigns/{self.db.campaign.id}/publish",
            json={"version_id": str(uuid.uuid4())},
        )
        self.assertEqual(response.status_code, 404)

    def test_publish_selects_campaign_default_version(self) -> None:
        self.db.campaign = Campaign(
            id=uuid.uuid4(),
            website_id=self.website.id,
            name="Owned campaign",
            status="draft",
        )
        self.db.version = PopupVersion(
            id=uuid.uuid4(),
            campaign_id=self.db.campaign.id,
            config_json=variant("A", "friendly")["config"],
            label="A",
            created_by="user",
        )
        response = self.client.post(
            f"/api/popups/campaigns/{self.db.campaign.id}/publish",
            json={"version_id": str(self.db.version.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.db.campaign.status, "published")
        self.assertEqual(self.db.campaign.default_version_id, self.db.version.id)
        self.assertIn(str(self.db.campaign.id), response.json()["embed_snippet"])

    def test_upload_rejects_unsupported_mime(self) -> None:
        response = self.client.post(
            "/api/popups/images",
            files={"image": ("fake.gif", b"GIF89a", "image/gif")},
        )
        self.assertEqual(response.status_code, 415)

    def test_upload_rejects_corrupt_image(self) -> None:
        response = self.client.post(
            "/api/popups/images",
            files={"image": ("broken.png", b"not an image", "image/png")},
        )
        self.assertEqual(response.status_code, 422)

    def test_upload_normalizes_valid_png_to_webp(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (12, 12), color=(28, 93, 53)).save(buffer, format="PNG")
        buffer.seek(0)
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = get_settings()
            with patch.object(settings, "media_dir", Path(temp_dir)), patch.object(
                settings, "public_api_base_url", "https://api.example"
            ):
                response = self.client.post(
                    "/api/popups/images",
                    files={"image": ("brand.png", buffer.getvalue(), "image/png")},
                )
            self.assertEqual(response.status_code, 200)
            uploaded_url = response.json()["url"]
            filename = uploaded_url.rsplit("/", 1)[-1]
            self.assertTrue(filename.endswith(".webp"))
            self.assertTrue((Path(temp_dir) / filename).exists())


if __name__ == "__main__":
    unittest.main()