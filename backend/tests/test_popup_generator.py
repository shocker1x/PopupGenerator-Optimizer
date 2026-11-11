import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.popup import PopupVariants
from app.schemas.website import WebsiteAnalysis
from app.services.popup_generator import PopupGenerationError, generate_popup_variants


def sample_analysis(approval_required: bool = True) -> WebsiteAnalysis:
    return WebsiteAnalysis(
        business_type="Outdoor apparel store",
        target_audience="People looking for durable everyday outdoor clothing",
        brand_tone="Practical and welcoming",
        products=["Jackets", "Shirts"],
        brand_colors=["#174A38", "#B15A34"],
        suggested_offer={
            "text": "Explore the new collection",
            "requires_owner_approval": approval_required,
        },
    )


def variant(label: str, tone: str, offer: dict | None = None) -> dict:
    return {
        "label": label,
        "tone": tone,
        "config": {
            "headline": f"A better way to wear {tone}",
            "description": "Discover practical layers for everyday adventures.",
            "cta": "Join the list",
            "email_placeholder": "Your email address",
            "offer": offer,
            "layout": "centered",
            "trigger": {
                "type": "time_delay",
                "delay_seconds": 5,
                "scroll_percentage": 50,
            },
            "theme": {
                "background_color": "#FFFFFF",
                "text_color": "#174A38",
                "accent_color": "#B15A34",
                "font": "georgia",
                "border_radius": 8,
            },
            "image": None,
            "consent_text": "By subscribing, you agree to receive email updates.",
        },
    }


def variants_json(offer: dict | None = None) -> str:
    return PopupVariants(
        variants=[
            variant("A", "friendly", offer),
            variant("B", "minimal", offer),
            variant("C", "bold", offer),
        ]
    ).model_dump_json()


class PopupGeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_preserves_approval_required_offer_on_every_variant(self) -> None:
        altered_offer = {"text": "Model changed this", "requires_owner_approval": False}
        with patch(
            "app.services.popup_generator._request_variants",
            new=AsyncMock(return_value=variants_json(altered_offer)),
        ):
            generated = await generate_popup_variants(sample_analysis(True))

        for item in generated.variants:
            self.assertEqual(item.config.offer.text, "Explore the new collection")
            self.assertTrue(item.config.offer.requires_owner_approval)

    async def test_preserves_existing_approved_promotion(self) -> None:
        analysis = sample_analysis(False)
        analysis.suggested_offer.text = "Free shipping on orders over $75"
        model_offer = {"text": "Invented 50% off", "requires_owner_approval": True}
        with patch(
            "app.services.popup_generator._request_variants",
            new=AsyncMock(return_value=variants_json(model_offer)),
        ):
            generated = await generate_popup_variants(analysis)

        for item in generated.variants:
            self.assertEqual(item.config.offer.text, "Free shipping on orders over $75")
            self.assertFalse(item.config.offer.requires_owner_approval)

    async def test_invalid_output_retries_once(self) -> None:
        request = AsyncMock(side_effect=["not JSON", variants_json()])
        with patch("app.services.popup_generator._request_variants", new=request):
            generated = await generate_popup_variants(sample_analysis())

        self.assertEqual(request.await_count, 2)
        self.assertEqual([item.label for item in generated.variants], ["A", "B", "C"])

    async def test_invalid_output_after_retry_is_an_error(self) -> None:
        request = AsyncMock(return_value='{"variants":[]}')
        with patch("app.services.popup_generator._request_variants", new=request):
            with self.assertRaisesRegex(PopupGenerationError, "did not match"):
                await generate_popup_variants(sample_analysis())
        self.assertEqual(request.await_count, 2)

    async def test_schema_rejects_duplicate_tones(self) -> None:
        repeated_tone_variants = [
            variant("A", "friendly"),
            variant("B", "friendly"),
            variant("C", "bold"),
        ]
        with self.assertRaisesRegex(ValueError, "distinct tone"):
            PopupVariants.model_validate({"variants": repeated_tone_variants})

    async def test_schema_rejects_invalid_theme_color(self) -> None:
        invalid_variant = variant("A", "friendly")
        invalid_variant["config"]["theme"]["accent_color"] = "orange"
        with self.assertRaises(ValueError):
            PopupVariants.model_validate(
                {
                    "variants": [
                        invalid_variant,
                        variant("B", "minimal"),
                        variant("C", "bold"),
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()