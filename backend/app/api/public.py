import uuid
from datetime import datetime, timezone
from enum import StrEnum

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Event, PopupVersion, Subscriber, Website
from app.services.public_api import (
    enforce_rate_limit,
    get_campaign_origin,
    preflight_response,
    validate_campaign_origin,
)

router = APIRouter(prefix="/api/public", tags=["public"])


class PublishedPopupConfig(BaseModel):
    campaign_id: uuid.UUID
    version_id: uuid.UUID
    config: dict

    model_config = ConfigDict(extra="forbid")


class PublicEventType(StrEnum):
    IMPRESSION = "impression"
    SUBMIT = "submit"
    CLOSE = "close"


class PublicEventRequest(BaseModel):
    version_id: uuid.UUID
    visitor_id: str = Field(min_length=16, max_length=100, pattern="^[A-Za-z0-9_-]+$")
    type: PublicEventType

    model_config = ConfigDict(extra="forbid")


class PublicSubscribeRequest(BaseModel):
    version_id: uuid.UUID
    visitor_id: str = Field(min_length=16, max_length=100, pattern="^[A-Za-z0-9_-]+$")
    email: EmailStr
    consent_text: str = Field(min_length=10, max_length=240)

    model_config = ConfigDict(extra="forbid")


class PublicEventResponse(BaseModel):
    accepted: bool = True


class PublicSubscribeResponse(BaseModel):
    accepted: bool = True
    duplicate: bool


@router.get("/campaigns/{campaign_id}/config", response_model=PublishedPopupConfig)
def get_published_popup_config(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> PublishedPopupConfig:
    website_url = db.scalar(
        select(Website.url)
        .join(Campaign, Campaign.website_id == Website.id)
        .where(Campaign.id == campaign_id)
    )
    if website_url is None:
        raise HTTPException(status_code=404, detail="Published popup not found")

    allowed_origin = get_campaign_origin(db, campaign_id)
    request_origin = request.headers.get("origin")
    if request_origin and request_origin != allowed_origin:
        raise HTTPException(status_code=403, detail="Origin is not allowed for this campaign")
    if request_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Vary"] = "Origin"
    enforce_rate_limit(request, campaign_id, "config", limit=120, window_seconds=60)

    version = db.scalar(
        select(PopupVersion)
        .join(Campaign, Campaign.default_version_id == PopupVersion.id)
        .where(
            Campaign.id == campaign_id,
            Campaign.status == "published",
            PopupVersion.campaign_id == Campaign.id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Published popup not found")

    return PublishedPopupConfig(
        campaign_id=campaign_id,
        version_id=version.id,
        config=version.config_json,
    )


def _published_campaign_version(db: Session, campaign_id: uuid.UUID, version_id: uuid.UUID):
    version = db.scalar(
        select(PopupVersion)
        .join(Campaign, Campaign.id == PopupVersion.campaign_id)
        .where(
            Campaign.id == campaign_id,
            Campaign.status == "published",
            PopupVersion.id == version_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Published popup version not found")
    return version


@router.options("/campaigns/{campaign_id}/events", include_in_schema=False)
def events_preflight(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    return preflight_response(db, campaign_id, request, response)


@router.options("/campaigns/{campaign_id}/subscribe", include_in_schema=False)
def subscribe_preflight(
    campaign_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    return preflight_response(db, campaign_id, request, response)


@router.post(
    "/campaigns/{campaign_id}/events",
    response_model=PublicEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def record_public_event(
    campaign_id: uuid.UUID,
    payload: PublicEventRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> PublicEventResponse:
    validate_campaign_origin(db, campaign_id, request, response)
    enforce_rate_limit(request, campaign_id, "events", limit=60, window_seconds=60)
    version = _published_campaign_version(db, campaign_id, payload.version_id)
    db.add(
        Event(
            campaign_id=campaign_id,
            version_id=version.id,
            type=payload.type.value,
            visitor_id=payload.visitor_id,
        )
    )
    db.commit()
    return PublicEventResponse()


@router.post(
    "/campaigns/{campaign_id}/subscribe",
    response_model=PublicSubscribeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def subscribe_public_visitor(
    campaign_id: uuid.UUID,
    payload: PublicSubscribeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> PublicSubscribeResponse:
    validate_campaign_origin(db, campaign_id, request, response)
    enforce_rate_limit(request, campaign_id, "subscribe", limit=10, window_seconds=600)
    version = _published_campaign_version(db, campaign_id, payload.version_id)
    expected_consent = version.config_json.get("consent_text", "")
    if payload.consent_text.strip() != expected_consent:
        raise HTTPException(status_code=422, detail="Consent text does not match the popup")
    email = str(payload.email).strip().lower()
    existing = db.scalar(
        select(Subscriber).where(
            Subscriber.campaign_id == campaign_id,
            Subscriber.email == email,
        )
    )
    if existing is not None:
        return PublicSubscribeResponse(duplicate=True)

    db.add(
        Subscriber(
            campaign_id=campaign_id,
            email=email,
            consent_text=payload.consent_text.strip(),
            consented_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        Event(
            campaign_id=campaign_id,
            version_id=version.id,
            type=PublicEventType.SUBMIT.value,
            visitor_id=payload.visitor_id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Subscriber).where(
                Subscriber.campaign_id == campaign_id,
                Subscriber.email == email,
            )
        )
        if existing is None:
            raise
        return PublicSubscribeResponse(duplicate=True)
    return PublicSubscribeResponse(duplicate=False)