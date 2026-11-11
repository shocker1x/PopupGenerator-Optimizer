import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services.url_safety import SafeURL
from app.services.website_analyzer import (
    BrowserFallbackUnavailable,
    FetchedResponse,
    MAX_RESPONSE_BYTES,
    WebsiteFetchError,
    _extract_document,
    _playwright_extract,
    fetch_html,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "store_page.html"
FIXTURE_HTML = FIXTURE_PATH.read_text(encoding="utf-8")


def safe_url(hostname: str = "store.example") -> SafeURL:
    return SafeURL(
        scheme="https",
        hostname=hostname,
        port=443,
        addresses=("93.184.216.34",),
        path_and_query="/",
        authority=hostname,
    )


class WebsiteExtractionTests(unittest.TestCase):
    def test_extracts_brand_content_assets_colors_and_promotions(self) -> None:
        data = _extract_document(FIXTURE_HTML, "https://store.example/")

        self.assertEqual(data.title, "Northstar Outfitters")
        self.assertEqual(
            data.meta_description,
            "Thoughtful outdoor clothing for everyday adventures.",
        )
        self.assertEqual(data.headings[0], "Made for the long way home")
        self.assertIn("Free shipping on orders over $75.", data.promotions)
        self.assertEqual(data.brand_colors, ["#174A38", "#B15A34"])
        self.assertIn("https://store.example/collections/new", data.links)
        self.assertIn("https://store.example/assets/jacket.jpg", data.image_candidates)
        self.assertIn("https://store.example/assets/brand-mark.png", data.logo_candidates)
        self.assertNotIn("This hidden text", data.visible_text)
        self.assertNotIn("not visible source text", data.visible_text)


class WebsiteFetchTests(unittest.IsolatedAsyncioTestCase):
    async def test_redirect_target_is_validated_before_fetch(self) -> None:
        redirect_response = FetchedResponse(
            status_code=302,
            headers={"location": "https://final.example/page"},
            body=b"",
        )
        final_response = FetchedResponse(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=b"<html><title>ok</title></html>",
        )
        with (
            patch(
                "app.services.website_analyzer.validate_url",
                new=AsyncMock(side_effect=[safe_url(), safe_url("final.example")]),
            ) as validate,
            patch(
                "app.services.website_analyzer._request_pinned",
                new=AsyncMock(side_effect=[redirect_response, final_response]),
            ) as request,
        ):
            html, final_url = await fetch_html("https://store.example/")

        self.assertEqual(final_url, "https://final.example/page")
        self.assertIn("<title>ok</title>", html)
        self.assertEqual(validate.await_count, 2)
        self.assertEqual(request.await_args_list[1].args[0].hostname, "final.example")

    async def test_rejects_non_html_response(self) -> None:
        with (
            patch(
                "app.services.website_analyzer.validate_url",
                new=AsyncMock(return_value=safe_url()),
            ),
            patch(
                "app.services.website_analyzer._request_pinned",
                new=AsyncMock(
                    return_value=FetchedResponse(
                        status_code=200,
                        headers={"content-type": "application/pdf"},
                        body=b"%PDF",
                    )
                ),
            ),
        ):
            with self.assertRaisesRegex(WebsiteFetchError, "did not return HTML"):
                await fetch_html("https://store.example/")

    async def test_rejects_response_over_size_limit(self) -> None:
        with (
            patch(
                "app.services.website_analyzer.validate_url",
                new=AsyncMock(return_value=safe_url()),
            ),
            patch(
                "app.services.website_analyzer._request_pinned",
                new=AsyncMock(
                    return_value=FetchedResponse(
                        status_code=200,
                        headers={"content-type": "text/html"},
                        body=b"x" * (MAX_RESPONSE_BYTES + 1),
                    )
                ),
            ),
        ):
            with self.assertRaisesRegex(WebsiteFetchError, "too large"):
                await fetch_html("https://store.example/")

    async def test_caps_redirects(self) -> None:
        response = FetchedResponse(
            status_code=302,
            headers={"location": "/next"},
            body=b"",
        )
        with (
            patch(
                "app.services.website_analyzer.validate_url",
                new=AsyncMock(return_value=safe_url()),
            ) as validate,
            patch(
                "app.services.website_analyzer._request_pinned",
                new=AsyncMock(return_value=response),
            ),
        ):
            with self.assertRaisesRegex(WebsiteFetchError, "redirect limit"):
                await fetch_html("https://store.example/", max_redirects=2)

        self.assertEqual(validate.await_count, 3)

    async def test_browser_fallback_fails_closed(self) -> None:
        with patch(
            "app.services.website_analyzer.validate_url",
            new=AsyncMock(return_value=safe_url()),
        ):
            with self.assertRaises(BrowserFallbackUnavailable):
                await _playwright_extract("https://store.example/")


if __name__ == "__main__":
    unittest.main()