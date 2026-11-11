import unittest
from unittest.mock import AsyncMock, patch

from app.services.url_safety import UnsafeURLError, validate_url


class URLSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_non_http_schemes_without_resolving(self) -> None:
        with patch(
            "app.services.url_safety._resolve_addresses", new_callable=AsyncMock
        ) as resolve:
            with self.assertRaises(UnsafeURLError):
                await validate_url("file:///etc/passwd")
        resolve.assert_not_awaited()

    async def test_rejects_private_ip_literal(self) -> None:
        with self.assertRaises(UnsafeURLError):
            await validate_url("http://127.0.0.1/admin")

    async def test_rejects_private_answer_in_mixed_dns_results(self) -> None:
        with patch(
            "app.services.url_safety._resolve_addresses",
            new=AsyncMock(return_value={"93.184.216.34", "10.0.0.8"}),
        ):
            with self.assertRaises(UnsafeURLError):
                await validate_url("https://store.example")

    async def test_returns_public_ip_pin_and_preserves_request_path(self) -> None:
        with patch(
            "app.services.url_safety._resolve_addresses",
            new=AsyncMock(return_value={"93.184.216.34"}),
        ):
            safe_url = await validate_url("https://Store.Example/catalog?q=summer#top")

        self.assertEqual(safe_url.hostname, "store.example")
        self.assertEqual(safe_url.authority, "store.example")
        self.assertEqual(safe_url.path_and_query, "/catalog?q=summer")
        self.assertEqual(
            safe_url.pinned_url(safe_url.addresses[0]),
            "https://93.184.216.34/catalog?q=summer",
        )

    async def test_rejects_url_credentials(self) -> None:
        with self.assertRaises(UnsafeURLError):
            await validate_url("https://user:pass@store.example")


if __name__ == "__main__":
    unittest.main()