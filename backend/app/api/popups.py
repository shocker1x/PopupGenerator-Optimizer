import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import Campaign, PopupVersion, User, Website
from app.schemas.popup import (
    CampaignDraftResponse,
    CreateCampaignRequest,
    GeneratePopupsRequest,
    GeneratePopupsResponse,
    ImageUploadResponse,
    PopupVersionResponse,
    PublishCampaignRequest,
    PublishCampaignResponse,
    RegeneratePopupRequest,
    UpdatePopupVersionRequest,
)
from app.services.popup_regenerator import PopupRegenerationError, regenerate_popup
from app.services.popup_generator import PopupGenerationError, generate_popup_variants

router = APIRouter(prefix="/api/popups", tags=["popups"])


@router.post("/generate", response_model=GeneratePopupsResponse)
async def generate_popups(
    payload: GeneratePopupsRequest,
    _current_user: User = Depends(get_current_user),
) -> GeneratePopupsResponse:
    try:
        generated = await generate_popup_variants(payload.analysis)
    except PopupGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return GeneratePopupsResponse(variants=generated.variants)


@router.post("/campaigns", response_model=CampaignDraftResponse, status_code=201)
def create_campaign_draft(
    payload: CreateCampaignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignDraftResponse:
    website = db.scalar(
        select(Website).where(
            Website.id == payload.website_id,
            Website.user_id == current_user.id,
        )
    )
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")

    campaign = Campaign(website_id=website.id, name=payload.name, status="draft")
    db.add(campaign)
    db.flush()
    versions = [
        PopupVersion(
            campaign_id=campaign.id,
            config_json=variant.config.model_dump(mode="json"),
            label=variant.label,
            created_by="ai",
        )
        for variant in payload.variants
    ]
    db.add_all(versions)
    db.commit()
    db.refresh(campaign)
    for version in versions:
        db.refresh(version)

    return CampaignDraftResponse(
        id=campaign.id,
        website_id=campaign.website_id,
        name=campaign.name,
        status=campaign.status,
        versions=[
            PopupVersionResponse(
                id=version.id,
                label=version.label,
                config=version.config_json,
            )
            for version in versions
        ],
    )


def _owned_version(db: Session, version_id: uuid.UUID, user_id: uuid.UUID) -> PopupVersion:
    version = db.scalar(
        select(PopupVersion)
        .join(Campaign, PopupVersion.campaign_id == Campaign.id)
        .join(Website, Campaign.website_id == Website.id)
        .where(PopupVersion.id == version_id, Website.user_id == user_id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Popup version not found")
    return version


@router.patch("/versions/{version_id}", response_model=PopupVersionResponse)
def update_popup_version(
    version_id: uuid.UUID,
    payload: UpdatePopupVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PopupVersionResponse:
    version = _owned_version(db, version_id, current_user.id)
    current_config = payload.config.model_dump(mode="json")
    previous_config = version.config_json
    for protected_field in ("offer", "consent_text", "email_placeholder", "layout"):
        current_config[protected_field] = previous_config[protected_field]
    version.config_json = current_config
    version.created_by = "user"
    db.commit()
    db.refresh(version)
    return PopupVersionResponse(
        id=version.id,
        label=version.label,
        config=version.config_json,
    )


@router.post("/versions/{version_id}/regenerate", response_model=PopupVersionResponse)
async def regenerate_popup_version(
    version_id: uuid.UUID,
    payload: RegeneratePopupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PopupVersionResponse:
    version = _owned_version(db, version_id, current_user.id)
    from app.schemas.popup import PopupConfig

    try:
        updated_config = await regenerate_popup(
            PopupConfig.model_validate(version.config_json),
            payload.instruction,
        )
    except PopupRegenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    version.config_json = updated_config.model_dump(mode="json")
    version.created_by = "ai"
    db.commit()
    db.refresh(version)
    return PopupVersionResponse(
        id=version.id,
        label=version.label,
        config=updated_config,
    )


@router.post(
    "/campaigns/{campaign_id}/publish",
    response_model=PublishCampaignResponse,
)
def publish_campaign(
    campaign_id: uuid.UUID,
    payload: PublishCampaignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PublishCampaignResponse:
    campaign = db.scalar(
        select(Campaign)
        .join(Website, Campaign.website_id == Website.id)
        .where(Campaign.id == campaign_id, Website.user_id == current_user.id)
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    version = db.scalar(
        select(PopupVersion).where(
            PopupVersion.id == payload.version_id,
            PopupVersion.campaign_id == campaign.id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Popup version not found")

    campaign.default_version_id = version.id
    campaign.status = "published"
    db.commit()
    base_url = get_settings().public_api_base_url.rstrip("/")
    snippet = (
        f'<script src="{base_url}/widget.js" '
        f'data-campaign-id="{campaign.id}" async></script>'
    )
    return PublishCampaignResponse(
        campaign_id=campaign.id,
        status=campaign.status,
        default_version_id=version.id,
        embed_snippet=snippet,
    )


MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/images", response_model=ImageUploadResponse)
async def upload_popup_image(
    image: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
) -> ImageUploadResponse:
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")
    raw_image = await image.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    await image.close()
    if len(raw_image) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")

    try:
        with Image.open(BytesIO(raw_image)) as source:
            if source.width > 6000 or source.height > 6000:
                raise HTTPException(status_code=422, detail="Image dimensions are too large")
            source.verify()
        with Image.open(BytesIO(raw_image)) as source:
            converted = source.convert("RGB")
            filename = f"{uuid.uuid4().hex}.webp"
            media_dir = get_settings().media_dir
            media_dir.mkdir(parents=True, exist_ok=True)
            converted.save(media_dir / filename, format="WEBP", quality=86, method=5)
    except OSError as exc:
        raise HTTPException(status_code=422, detail="File is not a valid image") from exc

    base_url = get_settings().public_api_base_url.rstrip("/")
    return ImageUploadResponse(url=f"{base_url}/media/{filename}")