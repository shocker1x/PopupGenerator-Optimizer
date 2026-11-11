import json

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.popup import PopupVariants
from app.schemas.website import WebsiteAnalysis

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class PopupGenerationError(RuntimeError):
    pass


def _prompt(analysis: WebsiteAnalysis) -> str:
    return (
        "Create exactly three distinct email signup popup variants as structured JSON. "
        "Use labels A, B, and C exactly once, with one friendly, one minimal, and one bold "
        "tone. Use only facts and products supported by the analysis. Keep copy concise and "
        "appropriate to the audience. Use the supplied brand colors, choosing valid hex values. "
        "Do not invent discounts, shipping promises, guarantees, or other promotions. Preserve "
        "the supplied offer text and its requires_owner_approval flag exactly. If approval is "
        "required, do not include the suggested offer in the headline, description, or CTA; "
        "it is for the owner to review. Use a valid HTTP(S) image URL only when an image is "
        "strongly relevant; otherwise set image to null. Include clear consent text. "
        "Use trigger type time_delay, exit_intent, or scroll_percentage and set the matching "
        "parameters within the schema bounds.\n\n"
        "Website analysis:\n"
        f"{analysis.model_dump_json()}"
    )


async def _request_variants(prompt: str) -> str:
    settings = get_settings()
    if settings.gemini_api_key is None or not settings.gemini_model:
        raise PopupGenerationError("Gemini API key and model must be configured")

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": PopupVariants.model_json_schema(),
            "temperature": 0.7,
        },
    }
    endpoint = f"{GEMINI_API_BASE}/{settings.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0), trust_env=False
        ) as client:
            response = await client.post(
                endpoint,
                headers={"x-goog-api-key": settings.gemini_api_key.get_secret_value()},
                json=request_body,
            )
    except httpx.HTTPError as exc:
        raise PopupGenerationError("Gemini request failed") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise PopupGenerationError(f"Gemini returned HTTP {response.status_code}")
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise PopupGenerationError("Gemini returned an empty or invalid response") from exc
    if not isinstance(text, str):
        raise PopupGenerationError("Gemini returned an invalid response")
    return text


async def generate_popup_variants(analysis: WebsiteAnalysis) -> PopupVariants:
    prompt = _prompt(analysis)
    for attempt in range(2):
        try:
            raw_response = await _request_variants(prompt)
            variants = PopupVariants.model_validate_json(raw_response)
            return variants.preserve_analysis_offer(analysis)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            if attempt == 1:
                raise PopupGenerationError(
                    "Gemini returned popup variants that did not match the required schema"
                ) from exc
    raise PopupGenerationError("Popup generation failed")