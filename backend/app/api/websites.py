from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models import User, Website
from app.schemas.website import AnalyzeWebsiteRequest, WebsiteAnalysisResponse
from app.services.gemini_analyzer import GeminiAnalysisError, generate_website_analysis
from app.services.url_safety import UnsafeURLError
from app.services.website_analyzer import WebsiteFetchError, analyze_website

router = APIRouter(prefix="/api/websites", tags=["websites"])


@router.post("/analyze", response_model=WebsiteAnalysisResponse)
async def analyze_and_save_website(
    payload: AnalyzeWebsiteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebsiteAnalysisResponse:
    try:
        extracted = await analyze_website(str(payload.url))
    except (UnsafeURLError, WebsiteFetchError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        analysis = await generate_website_analysis(extracted)
    except GeminiAnalysisError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    website = db.scalar(
        select(Website).where(
            Website.user_id == current_user.id,
            Website.url == extracted.url,
        )
    )
    if website is None:
        website = Website(user_id=current_user.id, url=extracted.url)
        db.add(website)

    website.analysis_json = analysis.model_dump(mode="json")
    website.analyzed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(website)

    return WebsiteAnalysisResponse(
        website_id=website.id,
        url=website.url,
        analysis=analysis,
    )