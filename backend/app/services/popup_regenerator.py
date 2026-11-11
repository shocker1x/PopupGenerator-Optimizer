import json

import httpx
from pydantic import ValidationError

from app.config import get_settings
from app.schemas.popup import (
    PopupConfig,
    PopupConfigPatch,
    PopupTheme,
    PopupTrigger,
)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class PopupRegenerationError(RuntimeError):
    pass


def _prompt(config: PopupConfig, instruction: str) -> str:
    return (
        "Revise only the popup fields that are relevant to the owner's instruction. "
        "Return a JSON object containing only changed fields. Allowed fields are headline, "
        "description, cta, trigger (type, delay_seconds, scroll_percentage), theme "
        "(background_color, text_color, accent_color, font, border_radius), and image. "
        "Do not return offer, consent_text, email_placeholder, or layout. Do not change any "
        "other fields. Treat the instruction as a request for copy/design changes only; do "
        "not create discounts, promises, or factual claims. Use valid schema enum and color "
        "values.\n\n"
        f"Current popup config:\n{config.model_dump_json()}\n\n"
        f"Owner instruction:\n{json.dumps(instruction, ensure_ascii=True)}"
    )


async def _request_patch(prompt: str) -> str:
    settings = get_settings()
    if settings.gemini_api_key is None or not settings.gemini_model:
        raise PopupRegenerationError("Gemini API key and model must be configured")

    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": PopupConfigPatch.model_json_schema(),
            "temperature": 0.6,
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
        raise PopupRegenerationError("Gemini request failed") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise PopupRegenerationError(f"Gemini returned HTTP {response.status_code}")
    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise PopupRegenerationError("Gemini returned an empty or invalid response") from exc
    if not isinstance(text, str):
        raise PopupRegenerationError("Gemini returned an invalid response")
    return text


def apply_popup_patch(config: PopupConfig, patch: PopupConfigPatch) -> PopupConfig:
    updated = config.model_dump(mode="json")
    changes = patch.model_dump(mode="json", exclude_unset=True)
    for field, value in changes.items():
        if field == "theme":
            updated["theme"].update(value)
        elif field == "trigger":
            updated["trigger"].update(value)
        else:
            updated[field] = value
    return PopupConfig.model_validate(updated)


async def regenerate_popup(
    config: PopupConfig,
    instruction: str,
) -> PopupConfig:
    prompt = _prompt(config, instruction)
    for attempt in range(2):
        try:
            raw_patch = await _request_patch(prompt)
            patch = PopupConfigPatch.model_validate_json(raw_patch)
            if not patch.model_fields_set:
                raise ValueError("Gemini returned no editable field changes")
            return apply_popup_patch(config, patch)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            if attempt == 1:
                raise PopupRegenerationError(
                    "Gemini returned changes that did not match the editable popup schema"
                ) from exc
    raise PopupRegenerationError("Popup regeneration failed")