import unittest
import uuid

from fastapi.testclient import TestClient
from fastapi import HTTPException
from starlette.requests import Request

from app.database import get_db
from app.main import app
from app.models import Event, PopupVersion, Subscriber
from app.services.public_api import enforce_rate_limit


class FakeDatabase:
    def __init__(self) -> None:
        self.version = None
        self.website_url = "https://store.example/"
        self.subscriber = None
        self.added = []

    def scalar(self, query):
        statement = str(query)
        if "websites.url" in statement:
            return self.website_url
        if "subscribers." in statement:
            return self.subscriber
        return self.version

    def add(self, item):
        self.added.append(item)

    def commit(self):
        pass

    def rollback(self):
        pass


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

    def test_origin_comparison_normalizes_host_case_and_default_port(self) -> None:
        campaign_id = uuid.uuid4()
        self.db.website_url = "HTTPS://Store.Example:443/shop"
        self.db.version = PopupVersion(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            config_json={"headline": "Hello"},
            label="A",
            created_by="user",
        )
        response = self.client.get(
            f"/api/public/campaigns/{campaign_id}/config",
            headers={"Origin": "https://store.example"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://store.example")

    def test_widget_script_is_served_as_javascript(self) -> None:
        response = self.client.get("/widget.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response.headers["content-type"])
        self.assertIn("attachShadow", response.text)

    def test_widget_event_records_impression(self) -> None:
        campaign_id = uuid.uuid4()
        version_id = uuid.uuid4()
        self.db.version = PopupVersion(
            id=version_id,
            campaign_id=campaign_id,
            config_json={"consent_text": "By subscribing, you agree to updates."},
            label="A",
            created_by="user",
        )
        response = self.client.post(
            f"/api/public/campaigns/{campaign_id}/events",
            headers={"Origin": "https://store.example"},
            json={"version_id": str(version_id), "visitor_id": "visitor-identifier-1234", "type": "impression"},
        )
        self.assertEqual(response.status_code, 202)
        event = next(item for item in self.db.added if isinstance(item, Event))
        self.assertEqual(event.type, "impression")
        self.assertEqual(event.campaign_id, campaign_id)

    def test_widget_events_reject_unapproved_origin(self) -> None:
        campaign_id = uuid.uuid4()
        response = self.client.post(
            f"/api/public/campaigns/{campaign_id}/events",
            headers={"Origin": "https://unrelated.example"},
            json={"version_id": str(uuid.uuid4()), "visitor_id": "visitor-identifier-1234", "type": "close"},
        )
        self.assertEqual(response.status_code, 403)

    def test_event_preflight_returns_campaign_origin_and_allowed_headers(self) -> None:
        response = self.client.options(
            f"/api/public/campaigns/{uuid.uuid4()}/events",
            headers={
                "Origin": "https://store.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["access-control-allow-origin"], "https://store.example")
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_event_rate_limit_rejects_excess_requests(self) -> None:
        campaign_id = uuid.uuid4()
        request = Request({"type": "http", "client": ("rate-test", 1234)})
        enforce_rate_limit(request, campaign_id, "unit-test", limit=1, window_seconds=60)
        with self.assertRaises(HTTPException) as raised:
            enforce_rate_limit(request, campaign_id, "unit-test", limit=1, window_seconds=60)
        self.assertEqual(raised.exception.status_code, 429)

    def test_public_post_rejects_oversized_content_length(self) -> None:
        response = self.client.post(
            f"/api/public/campaigns/{uuid.uuid4()}/events",
            headers={"Content-Length": str(20 * 1024)},
            content=b"{}",
        )
        self.assertEqual(response.status_code, 413)

    def test_subscribe_stores_canonical_consent_and_submit_event(self) -> None:
        campaign_id = uuid.uuid4()
        version_id = uuid.uuid4()
        consent = "By subscribing, you agree to receive email updates."
        self.db.version = PopupVersion(
            id=version_id,
            campaign_id=campaign_id,
            config_json={"consent_text": consent},
            label="A",
            created_by="user",
        )
        response = self.client.post(
            f"/api/public/campaigns/{campaign_id}/subscribe",
            headers={"Origin": "https://store.example"},
            json={
                "version_id": str(version_id),
                "visitor_id": "visitor-identifier-1234",
                "email": "Person@Example.com",
                "consent_text": consent,
            },
        )
        self.assertEqual(response.status_code, 202)
        subscriber = next(item for item in self.db.added if isinstance(item, Subscriber))
        event = next(item for item in self.db.added if isinstance(item, Event))
        self.assertEqual(subscriber.email, "person@example.com")
        self.assertEqual(subscriber.consent_text, consent)
        self.assertEqual(event.type, "submit")

    def test_subscribe_rejects_changed_consent_text(self) -> None:
        campaign_id = uuid.uuid4()
        version_id = uuid.uuid4()
        self.db.version = PopupVersion(
            id=version_id,
            campaign_id=campaign_id,
            config_json={"consent_text": "The exact popup consent wording."},
            label="A",
            created_by="user",
        )
        response = self.client.post(
            f"/api/public/campaigns/{campaign_id}/subscribe",
            json={
                "version_id": str(version_id),
                "visitor_id": "visitor-identifier-1234",
                "email": "person@example.com",
                "consent_text": "A different consent statement that is long enough.",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_subscribe_returns_duplicate_without_new_rows(self) -> None:
        campaign_id = uuid.uuid4()
        version_id = uuid.uuid4()
        consent = "By subscribing, you agree to receive email updates."
        self.db.version = PopupVersion(
            id=version_id,
            campaign_id=campaign_id,
            config_json={"consent_text": consent},
            label="A",
            created_by="user",
        )
        self.db.subscriber = Subscriber(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            email="person@example.com",
            consent_text=consent,
        )
        response = self.client.post(
            f"/api/public/campaigns/{campaign_id}/subscribe",
            json={
                "version_id": str(version_id),
                "visitor_id": "visitor-identifier-1234",
                "email": "person@example.com",
                "consent_text": consent,
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()["duplicate"])
        self.assertEqual(self.db.added, [])


if __name__ == "__main__":
    unittest.main()