import unittest
from unittest.mock import AsyncMock, patch

from app.schemas.popup import PopupConfig
from app.schemas.popup import PopupConfigPatch
from app.services.popup_regenerator import (
    PopupRegenerationError,
    apply_popup_patch,
    regenerate_popup,
)
from backend.tests.test_popup_generator import variant


def sample_config() -> PopupConfig:
    return PopupConfig.model_validate(
        variant(
            "A",
            "friendly",
            {"text": "Approved offer", "requires_owner_approval": True},
        )["config"]
    )


class PopupRegeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_patch_schema_validates_color_values(self) -> None:
        patch = PopupConfigPatch.model_validate({"theme": {"accent_color": "#35694A"}})
        self.assertEqual(patch.theme.accent_color, "#35694A")
        with self.assertRaises(ValueError):
            PopupConfigPatch.model_validate({"theme": {"accent_color": "green"}})

    async def test_patch_changes_only_requested_editable_fields(self) -> None:
        config = sample_config()
        patch_data = {
            "headline": "A quieter kind of welcome",
            "theme": {"accent_color": "#35694A"},
        }
        from app.schemas.popup import PopupConfigPatch

        updated = apply_popup_patch(config, PopupConfigPatch.model_validate(patch_data))

        self.assertEqual(updated.headline, "A quieter kind of welcome")
        self.assertEqual(updated.theme.accent_color, "#35694A")
        self.assertEqual(updated.description, config.description)
        self.assertEqual(updated.theme.text_color, config.theme.text_color)
        self.assertEqual(updated.offer, config.offer)
        self.assertEqual(updated.consent_text, config.consent_text)
        self.assertEqual(updated.layout, config.layout)

    async def test_invalid_or_protected_fields_are_rejected_after_retry(self) -> None:
        request = AsyncMock(return_value='{"offer":{"text":"Changed","requires_owner_approval":false}}')
        with patch("app.services.popup_regenerator._request_patch", new=request):
            with self.assertRaisesRegex(PopupRegenerationError, "editable popup schema"):
                await regenerate_popup(sample_config(), "Make the headline simpler")
        self.assertEqual(request.await_count, 2)

    async def test_regeneration_merges_valid_patch(self) -> None:
        request = AsyncMock(return_value='{"headline":"A quieter kind of welcome"}')
        with patch("app.services.popup_regenerator._request_patch", new=request):
            updated = await regenerate_popup(sample_config(), "Make the headline simpler")
        self.assertEqual(updated.headline, "A quieter kind of welcome")
        self.assertEqual(updated.offer, sample_config().offer)


if __name__ == "__main__":
    unittest.main()