import hashlib
import threading
import time
from collections import defaultdict
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Campaign, Website

_rate_lock = threading.Lock()
_rate_windows: dict[str, list[float]] = defaultdict(list)


def get_campaign_origin(db: Session, campaign_id) -> str:
    website_url = db.scalar(
        select(Website.url)
        .join(Campaign, Campaign.website_id == Website.id)
        .where(Campaign.id == campaign_id)
    )
    if website_url is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    parsed = urlsplit(website_url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if ":" in hostname:
        hostname = f"[{hostname}]"
    port = parsed.port
    default_port = 443 if scheme == "https" else 80
    port_suffix = f":{port}" if port and port != default_port else ""
    return f"{scheme}://{hostname}{port_suffix}"


def assign_popup_version(campaign_id, visitor_id: str, version_ids: list) -> object:
    if not version_ids:
        raise ValueError("At least one popup version is required")
    stable_ids = sorted(version_ids, key=str)
    key = f"{campaign_id}:{visitor_id}".encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % len(stable_ids)
    return stable_ids[bucket]


def validate_campaign_origin(
    db: Session,
    campaign_id,
    request: Request,
    response: Response,
) -> str:
    allowed_origin = get_campaign_origin(db, campaign_id)
    request_origin = request.headers.get("origin")
    if request_origin and request_origin != allowed_origin:
        raise HTTPException(status_code=403, detail="Origin is not allowed for this campaign")
    if request_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Vary"] = "Origin"
    return allowed_origin


def preflight_response(
    db: Session,
    campaign_id,
    request: Request,
    response: Response,
) -> Response:
    allowed_origin = validate_campaign_origin(db, campaign_id, request, response)
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "600",
            "Vary": "Origin",
        },
    )


def enforce_rate_limit(
    request: Request,
    campaign_id,
    action: str,
    limit: int,
    window_seconds: int,
) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = f"{campaign_id}:{action}:{client_host}"
    now = time.monotonic()
    cutoff = now - window_seconds
    with _rate_lock:
        window = [timestamp for timestamp in _rate_windows[key] if timestamp > cutoff]
        if len(window) >= limit:
            _rate_windows[key] = window
            raise HTTPException(status_code=429, detail="Too many requests; try again later")
        window.append(now)
        _rate_windows[key] = window
        if len(_rate_windows) > 10_000:
            expired_keys = [
                candidate
                for candidate, timestamps in _rate_windows.items()
                if not timestamps or timestamps[-1] <= cutoff
            ]
            for candidate in expired_keys:
                _rate_windows.pop(candidate, None)