import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.website import WebsiteAnalysis
from app.services.gemini_analyzer import GeminiAnalysisError, generate_website_analysis
from app.services.website_analyzer import WebsiteData


def sample_site(promotions: list[str] | None = None) -> WebsiteData:
    return WebsiteData(
        url="https://store.example/",
        title="Northstar Outfitters",
        meta_description="Outdoor clothing for everyday adventures.",
        headings=["Made for the long way home"],
        visible_text="Jackets and shirts made for daily use.",
        links=[],
        image_candidates=[],
        logo_candidates=[],
        brand_colors=["#174A38"],
        promotions=promotions or [],
    )


def analysis_json(offer: str = "Get 10% off your first order") -> str:
    return WebsiteAnalysis(
        business_type="Outdoor apparel store",
        target_audience="People looking for durable everyday outdoor clothing",
        brand_tone="Practical and welcoming",
        products=["Jackets", "Shirts"],
        brand_colors=["#FFFFFF"],
        suggested_offer={"text": offer, "requires_owner_approval": False},
    ).model_dump_json()


class GeminiAnalyzerTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_promotion_is_enforced_exactly(self) -> None:
        with patch(
            "app.services.gemini_analyzer._request_analysis",
            new=AsyncMock(return_value=analysis_json("Invented 50% off")),
        ):
            result = await generate_website_analysis(
                sample_site(["Free shipping on orders over $75."])
            )

        self.assertEqual(result.suggested_offer.text, "Free shipping on orders over $75.")
        self.assertFalse(result.suggested_offer.requires_owner_approval)
        self.assertEqual(result.brand_colors, ["#174A38"])

    async def test_new_offer_requires_owner_approval(self) -> None:
        with patch(
            "app.services.gemini_analyzer._request_analysis",
            new=AsyncMock(return_value=analysis_json()),
        ):
            result = await generate_website_analysis(sample_site())

        self.assertTrue(result.suggested_offer.requires_owner_approval)

    async def test_invalid_json_retries_once_then_succeeds(self) -> None:
        request = AsyncMock(side_effect=["not json", analysis_json()])
        with patch("app.services.gemini_analyzer._request_analysis", new=request):
            result = await generate_website_analysis(sample_site())

        self.assertEqual(request.await_count, 2)
        self.assertEqual(result.business_type, "Outdoor apparel store")

    async def test_invalid_output_after_retry_returns_clear_error(self) -> None:
        request = AsyncMock(return_value='{"business_type":"Only one field"}')
        with patch("app.services.gemini_analyzer._request_analysis", new=request):
            with self.assertRaisesRegex(GeminiAnalysisError, "did not match"):
                await generate_website_analysis(sample_site())

        self.assertEqual(request.await_count, 2)

    async def test_schema_rejects_invalid_colors(self) -> None:
        with self.assertRaises(ValueError):
            WebsiteAnalysis.model_validate(
                {
                    "business_type": "Store",
                    "target_audience": "Outdoor customers",
                    "brand_tone": "Friendly",
                    "products": ["Jackets"],
                    "brand_colors": ["red"],
                    "suggested_offer": {
                        "text": "A suggested offer",
                        "requires_owner_approval": True,
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()