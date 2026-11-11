from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user
from app.models import User
from app.schemas.popup import GeneratePopupsRequest, GeneratePopupsResponse
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