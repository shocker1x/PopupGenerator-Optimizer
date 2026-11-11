import re
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from PIL import Image, UnidentifiedImageError

from app.config import get_settings
from app.services.url_safety import SafeURL, UnsafeURLError, validate_url

MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
MAX_TEXT_CHARS = 12_000
MIN_VISIBLE_TEXT_CHARS = 300
MAX_IMAGE_CANDIDATES = 20
MAX_LOGO_BYTES = 1_000_000
PROMOTION_RE = re.compile(
    r"\b(?:\d{1,2}\s*%\s*off|save\s+\d+|free\s+shipping|"
    r"free\s+delivery|sale|buy\s+one\s+get\s+one|\bBOGO\b)\b",
    re.IGNORECASE,
)
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")


class WebsiteFetchError(ValueError):
    pass


class BrowserFallbackUnavailable(WebsiteFetchError):
    pass


@dataclass
class FetchedResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


@dataclass
class WebsiteData:
    url: str
    title: str | None
    meta_description: str | None
    headings: list[str]
    visible_text: str
    links: list[str]
    image_candidates: list[str]
    logo_candidates: list[str]
    brand_colors: list[str]
    promotions: list[str]


async def _request_pinned(
    url: SafeURL,
    address: str,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> FetchedResponse:
    transport = httpx.AsyncHTTPTransport(retries=0)
    timeout = httpx.Timeout(10.0, connect=3.0)
    request_url = url.pinned_url(address)
    try:
        async with httpx.AsyncClient(
            transport=transport,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            headers={
                "Host": url.authority,
                "User-Agent": "PopupGenerator-Analyzer/0.1 (+website metadata fetcher)",
                "Accept": "text/html,application/xhtml+xml",
            },
        ) as client:
            request = client.build_request("GET", request_url)
            if url.scheme == "https":
                request.extensions["sni_hostname"] = url.hostname
            request.extensions["timeout"] = {
                "connect": 3.0,
                "read": 8.0,
                "write": 5.0,
                "pool": 3.0,
            }
            response = await client.send(request, stream=True)
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise WebsiteFetchError("Website response is too large")
                except ValueError:
                    pass
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise WebsiteFetchError("Website response is too large")
            return FetchedResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=bytes(body),
            )
    except httpx.HTTPError as exc:
        await transport.aclose()
        raise WebsiteFetchError("Could not fetch website") from exc


async def fetch_html(url: str, max_redirects: int = MAX_REDIRECTS) -> tuple[str, str]:
    current_url = url
    for redirect_number in range(max_redirects + 1):
        safe_url = await validate_url(current_url)
        response: FetchedResponse | None = None
        for address in safe_url.addresses:
            response = await _request_pinned(safe_url, address)
            if response.status_code not in {502, 503, 504}:
                break

        assert response is not None
        if len(response.body) > MAX_RESPONSE_BYTES:
            raise WebsiteFetchError("Website response is too large")
        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("location")
            if not location:
                raise WebsiteFetchError("Website returned an invalid redirect")
            if redirect_number >= max_redirects:
                raise WebsiteFetchError("Website exceeded the redirect limit")
            current_url = urljoin(current_url, location)
            continue

        if response.status_code < 200 or response.status_code >= 300:
            raise WebsiteFetchError(f"Website returned HTTP {response.status_code}")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise WebsiteFetchError("Website did not return HTML")
        charset = re.search(r"charset=([^;\s]+)", response.headers.get("content-type", ""))
        encoding = charset.group(1).strip("\"'") if charset else "utf-8"
        return response.body.decode(encoding, errors="replace"), current_url

    raise WebsiteFetchError("Website exceeded the redirect limit")


def _absolute_url(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    absolute = urljoin(base_url, value.strip())
    if absolute.startswith(("http://", "https://")):
        return absolute
    return None


def _extract_document(html: str, page_url: str) -> WebsiteData:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    meta_description = (
        description_tag.get("content", "").strip() if description_tag else None
    )

    headings = [
        heading.get_text(" ", strip=True)
        for heading in soup.find_all(["h1", "h2", "h3"])
        if heading.get_text(" ", strip=True)
    ][:30]

    color_sources = [
        tag.get("content", "")
        for tag in soup.find_all("meta", attrs={"name": re.compile("^theme-color$", re.I)})
    ]
    color_sources.extend(tag.get_text(" ", strip=True) for tag in soup.find_all("style"))
    color_sources.extend(tag.get("style", "") for tag in soup.find_all(style=True))

    for hidden in soup(["script", "style", "noscript", "template", "svg"]):
        hidden.decompose()
    for hidden in soup.select("[hidden], [aria-hidden='true']"):
        hidden.decompose()
    visible_text = " ".join(soup.stripped_strings)
    visible_text = re.sub(r"\s+", " ", visible_text)[:MAX_TEXT_CHARS]

    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        link = _absolute_url(anchor.get("href"), page_url)
        if link and link not in links:
            links.append(link)
        if len(links) >= 50:
            break

    image_candidates: list[str] = []
    for image in soup.find_all("img"):
        image_url = _absolute_url(image.get("src") or image.get("data-src"), page_url)
        if image_url and image_url not in image_candidates:
            image_candidates.append(image_url)
        if len(image_candidates) >= MAX_IMAGE_CANDIDATES:
            break

    logo_candidates: list[str] = []
    for meta in soup.find_all("meta", property=re.compile(r"^og:image$", re.I)):
        logo_url = _absolute_url(meta.get("content"), page_url)
        if logo_url and logo_url not in logo_candidates:
            logo_candidates.append(logo_url)
    for icon in soup.find_all("link", rel=re.compile(r"icon", re.I)):
        logo_url = _absolute_url(icon.get("href"), page_url)
        if logo_url and logo_url not in logo_candidates:
            logo_candidates.append(logo_url)
    for image in soup.select("header img, [role='banner'] img"):
        logo_url = _absolute_url(image.get("src") or image.get("data-src"), page_url)
        if logo_url and logo_url not in logo_candidates:
            logo_candidates.append(logo_url)
    if page_url.startswith("http"):
        logo_candidates.append(urljoin(page_url, "/favicon.ico"))
    logo_candidates = list(dict.fromkeys(logo_candidates))[:10]

    colors: list[str] = []
    for source in color_sources:
        for color in HEX_COLOR_RE.findall(source):
            normalized = color.upper()
            if len(normalized) == 4:
                normalized = "#" + "".join(char * 2 for char in normalized[1:])
            if normalized not in colors:
                colors.append(normalized)

    promotions: list[str] = []
    for text in soup.stripped_strings:
        for match in PROMOTION_RE.finditer(text):
            item = re.sub(r"\s+", " ", text).strip()
            if item and item not in promotions:
                promotions.append(item[:240])
            break
        if len(promotions) >= 20:
            break

    return WebsiteData(
        url=page_url,
        title=title or None,
        meta_description=meta_description or None,
        headings=headings,
        visible_text=visible_text,
        links=links,
        image_candidates=image_candidates,
        logo_candidates=logo_candidates,
        brand_colors=colors[:12],
        promotions=promotions,
    )


async def _extract_logo_colors(logo_urls: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    for logo_url in logo_urls[:3]:
        try:
            safe_logo = await validate_url(logo_url)
            response: FetchedResponse | None = None
            for address in safe_logo.addresses:
                response = await _request_pinned(
                    safe_logo, address, max_bytes=MAX_LOGO_BYTES
                )
                if response.status_code not in {502, 503, 504}:
                    break
            if response is None or response.status_code != 200:
                continue
            content_type = response.headers.get("content-type", "").split(";", 1)[0]
            if not content_type.startswith("image/"):
                continue
            image = Image.open(BytesIO(response.body)).convert("RGB")
            image.thumbnail((64, 64))
            for color, count in image.getcolors(4096) or []:
                if max(color) - min(color) > 18 and max(color) > 45:
                    counts["#%02X%02X%02X" % color] += count
        except (UnsafeURLError, WebsiteFetchError, UnidentifiedImageError, OSError):
            continue
    return [color for color, _ in counts.most_common(5)]


async def _playwright_extract(url: str) -> str:
    await validate_url(url)
    raise BrowserFallbackUnavailable(
        "JavaScript-rendered fallback is not enabled until its browser runtime can "
        "use a sandboxed, IP-pinned network transport"
    )


async def analyze_website(url: str) -> WebsiteData:
    html, final_url = await fetch_html(url)
    data = _extract_document(html, final_url)
    if len(data.visible_text) < MIN_VISIBLE_TEXT_CHARS:
        html = await _playwright_extract(final_url)
        data = _extract_document(html, final_url)
    logo_colors = await _extract_logo_colors(data.logo_candidates)
    data.brand_colors = list(dict.fromkeys(data.brand_colors + logo_colors))[:12]
    return data