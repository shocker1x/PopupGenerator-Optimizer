import uuid
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, PopupVersion, Website

router = APIRouter(prefix="/api/public", tags=["public"])


class PublishedPopupConfig(BaseModel):
    campaign_id: uuid.UUID
    version_id: uuid.UUID
    config: dict

    model_config = ConfigDict(extra="forbid")


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

    parsed_website = urlsplit(website_url)
    allowed_origin = f"{parsed_website.scheme}://{parsed_website.netloc}"
    request_origin = request.headers.get("origin")
    if request_origin and request_origin != allowed_origin:
        raise HTTPException(status_code=403, detail="Origin is not allowed for this campaign")
    if request_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Vary"] = "Origin"

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