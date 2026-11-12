import argparse
import random
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Campaign, Event, PopupVersion, Subscriber


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Insert clearly marked synthetic events for a campaign demo."
    )
    parser.add_argument("campaign_id", type=uuid.UUID)
    parser.add_argument("--impressions", type=int, default=200)
    parser.add_argument(
        "--submissions-per-version",
        required=True,
        help="Comma-separated synthetic signup counts in version-label order.",
    )
    parser.add_argument("--seed", type=int, default=41)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.impressions < 1:
        raise SystemExit("--impressions must be at least 1")
    try:
        submissions = [int(value.strip()) for value in args.submissions_per_version.split(",")]
    except ValueError as exc:
        raise SystemExit("--submissions-per-version must be comma-separated integers") from exc

    with SessionLocal() as db:
        campaign = db.get(Campaign, args.campaign_id)
        if campaign is None:
            raise SystemExit("Campaign not found")
        versions = db.scalars(
            select(PopupVersion)
            .where(PopupVersion.campaign_id == campaign.id)
            .order_by(PopupVersion.label)
        ).all()
        if len(versions) != len(submissions):
            raise SystemExit(
                f"Received {len(submissions)} signup counts for {len(versions)} versions"
            )
        if any(count < 0 or count > args.impressions for count in submissions):
            raise SystemExit("Each signup count must be between zero and --impressions")

        rng = random.Random(args.seed)
        run_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc)
        for version, signup_count in zip(versions, submissions, strict=True):
            visitor_indexes = set(rng.sample(range(args.impressions), signup_count))
            for index in range(args.impressions):
                visitor_id = f"seed-{run_id}-{version.label}-{index}"
                db.add(
                    Event(
                        campaign_id=campaign.id,
                        version_id=version.id,
                        type="impression",
                        visitor_id=visitor_id,
                        created_at=created_at,
                    )
                )
                if index in visitor_indexes:
                    email = f"seed-{run_id}-{version.label}-{index}@demo.invalid"
                    db.add(
                        Subscriber(
                            campaign_id=campaign.id,
                            email=email,
                            consent_text=version.config_json.get("consent_text", "Synthetic demo signup"),
                            consented_at=created_at,
                            created_at=created_at,
                        )
                    )
                    db.add(
                        Event(
                            campaign_id=campaign.id,
                            version_id=version.id,
                            type="submit",
                            visitor_id=visitor_id,
                            created_at=created_at,
                        )
                    )
        db.commit()
        print(
            f"Inserted synthetic data for campaign {campaign.id}: "
            f"{len(versions) * args.impressions} impressions and "
            f"{sum(submissions)} demo signups ({run_id})."
        )


if __name__ == "__main__":
    main()