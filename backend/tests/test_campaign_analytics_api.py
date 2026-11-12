import unittest
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models import Campaign, Event, PopupVersion, Subscriber, User


class ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class AnalyticsDatabase:
    def __init__(self):
        self.campaign = None
        self.versions = []
        self.events = []
        self.subscribers = []
        self.delete_calls = []

    def scalar(self, query):
        statement = str(query).lower()
        if "count(subscribers.id)" in statement:
            return len(self.subscribers)
        if "from subscribers" in statement and "subscribers.id" in statement:
            return next(
                (subscriber for subscriber in self.subscribers if str(subscriber.id) in statement),
                self.subscribers[0] if self.subscribers else None,
            )
        if "from campaigns" in statement:
            return self.campaign
        if "from popup_versions" in statement:
            return self.versions[0] if self.versions else None
        return None

    def scalars(self, query):
        statement = str(query).lower()
        if "from popup_versions" in statement:
            return ScalarRows(self.versions)
        if "from events" in statement:
            return ScalarRows(self.events)
        if "from subscribers" in statement:
            return ScalarRows(self.subscribers)
        return ScalarRows([])

    def delete(self, item):
        self.delete_calls.append(item)
        self.subscribers.remove(item)

    def commit(self):
        pass


class CampaignAnalyticsAPITests(unittest.TestCase):
    def setUp(self):
        self.db = AnalyticsDatabase()
        self.user = User(id=uuid.uuid4(), email="owner@example.com", password_hash="unused")
        self.campaign = Campaign(
            id=uuid.uuid4(), website_id=uuid.uuid4(), name="Northstar welcome", status="published",
            ab_test_enabled=True,
        )
        self.version_a = PopupVersion(
            id=uuid.uuid4(), campaign_id=self.campaign.id, config_json={}, label="A", created_by="ai"
        )
        self.version_b = PopupVersion(
            id=uuid.uuid4(), campaign_id=self.campaign.id, config_json={}, label="B", created_by="ai"
        )
        self.db.campaign = self.campaign
        self.db.versions = [self.version_a, self.version_b]
        self.db.events = [
            *[Event(campaign_id=self.campaign.id, version_id=self.version_a.id, type="impression", visitor_id=f"visitor-{i}") for i in range(100)],
            *[Event(campaign_id=self.campaign.id, version_id=self.version_a.id, type="submit", visitor_id=f"signup-{i}") for i in range(3)],
            *[Event(campaign_id=self.campaign.id, version_id=self.version_a.id, type="close", visitor_id=f"close-{i}") for i in range(2)],
            *[Event(campaign_id=self.campaign.id, version_id=self.version_b.id, type="impression", visitor_id=f"bvisitor-{i}") for i in range(50)],
            *[Event(campaign_id=self.campaign.id, version_id=self.version_b.id, type="submit", visitor_id=f"bsignup-{i}") for i in range(2)],
        ]
        consented_at = datetime(2026, 11, 12, tzinfo=timezone.utc)
        self.db.subscribers = [
            Subscriber(
                id=uuid.uuid4(), campaign_id=self.campaign.id, email=f"person{i}@example.com",
                consent_text="I agree to email updates.", consented_at=consented_at, created_at=consented_at,
            )
            for i in range(5)
        ]
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_analytics_uses_impressions_and_unique_subscriber_total(self):
        response = self.client.get(f"/api/popups/campaigns/{self.campaign.id}/analytics")
        self.assertEqual(response.status_code, 200)
        report = response.json()
        self.assertEqual(report["impressions"], 150)
        self.assertEqual(report["submissions"], 5)
        self.assertEqual(report["conversion_rate"], 3.33)
        by_label = {item["label"]: item for item in report["versions"]}
        self.assertEqual(by_label["A"]["conversion_rate"], 3.0)
        self.assertEqual(by_label["A"]["dismissals"], 2)
        self.assertEqual(by_label["B"]["conversion_rate"], 4.0)
        self.assertEqual(report["recommendation"]["decision"], "not_enough_data")
        self.assertTrue(report["ab_test_enabled"])

    def test_make_default_disables_rotation(self):
        response = self.client.post(
            f"/api/popups/campaigns/{self.campaign.id}/default",
            json={"version_id": str(self.version_a.id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.campaign.default_version_id, self.version_a.id)
        self.assertFalse(self.campaign.ab_test_enabled)

    def test_subscriber_csv_contains_consent_and_email(self):
        response = self.client.get(
            f"/api/popups/campaigns/{self.campaign.id}/subscribers.csv"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("email,consent_text,consented_at,created_at", response.text)
        self.assertIn("person0@example.com", response.text)
        self.assertIn("I agree to email updates.", response.text)

    def test_owner_can_delete_subscriber(self):
        subscriber = self.db.subscribers[0]
        response = self.client.delete(
            f"/api/popups/campaigns/{self.campaign.id}/subscribers/{subscriber.id}"
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(self.db.subscribers), 4)

    def test_non_owned_campaign_is_not_found(self):
        self.db.campaign = None
        response = self.client.get(f"/api/popups/campaigns/{uuid.uuid4()}/analytics")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()