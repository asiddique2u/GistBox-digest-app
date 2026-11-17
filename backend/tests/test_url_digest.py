import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from backend.app.agent.digest_models import DigestOutput
from app.services.url_digest import (
    UnsafeURL,
    _download_html,
    _extract_web_content,
    _validate_public_url,
)


client = TestClient(app)


class URLDigestTests(unittest.TestCase):
    def test_post_digest_returns_requested_detail_level(self) -> None:
        digest = DigestOutput(title="A Useful Digest", summary="Key points.")
        with patch("main.generate_url_digest", return_value=digest) as generate:
            response = client.post(
                "/digest",
                json={
                    "url": "https://example.com/article",
                    "detail_level": "detailed",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "url": "https://example.com/article",
                "detail_level": "detailed",
                "title": "A Useful Digest",
                "summary": "Key points.",
            },
        )
        generate.assert_called_once_with(
            "https://example.com/article",
            detail_level="detailed",
        )

    def test_post_digest_defaults_to_detailed(self) -> None:
        digest = DigestOutput(title="A Useful Digest", summary="Key points.")
        with patch("main.generate_url_digest", return_value=digest) as generate:
            response = client.post(
                "/digest",
                json={"url": "https://example.com/article"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail_level"], "detailed")
        generate.assert_called_once_with(
            "https://example.com/article",
            detail_level="detailed",
        )

    def test_post_digest_rejects_unknown_detail_level(self) -> None:
        with patch("main.generate_url_digest") as generate:
            response = client.post(
                "/digest",
                json={
                    "url": "https://example.com/article",
                    "detail_level": "extra-long",
                },
            )

        self.assertEqual(response.status_code, 422)
        generate.assert_not_called()

    def test_post_digest_rejects_non_http_urls(self) -> None:
        with patch("main.generate_url_digest") as generate:
            response = client.post("/digest", json={"url": "file:///etc/passwd"})

        self.assertEqual(response.status_code, 422)
        generate.assert_not_called()

    def test_post_digest_maps_unsafe_url_to_client_error(self) -> None:
        with patch(
            "main.generate_url_digest",
            side_effect=UnsafeURL("The URL must resolve to a public internet address"),
        ):
            response = client.post(
                "/digest",
                json={"url": "https://example.com/article"},
            )

        self.assertEqual(response.status_code, 400)

    def test_private_ip_url_is_rejected(self) -> None:
        with self.assertRaises(UnsafeURL):
            _validate_public_url("http://127.0.0.1/")

    def test_redirect_to_private_ip_is_rejected(self) -> None:
        redirect_response = MagicMock()
        redirect_response.is_redirect = True
        redirect_response.headers = {"location": "http://127.0.0.1/admin"}

        stream_context = MagicMock()
        stream_context.__enter__.return_value = redirect_response
        http_client = MagicMock()
        http_client.stream.return_value = stream_context
        client_context = MagicMock()
        client_context.__enter__.return_value = http_client

        with (
            patch(
                "app.services.url_digest.httpx.Client",
                return_value=client_context,
            ),
            patch(
                "app.services.url_digest._validate_public_url",
                side_effect=[
                    ("example.com", 443),
                    UnsafeURL("The URL must resolve to a public internet address"),
                ],
            ),
        ):
            with self.assertRaises(UnsafeURL):
                _download_html("https://example.com/article")

        http_client.stream.assert_called_once()

    def test_extracts_article_text_and_title(self) -> None:
        html = """
        <html>
          <head><title>Article About Reliable Systems</title></head>
          <body><article>
            <h1>Article About Reliable Systems</h1>
            <p>Reliable systems need careful design and robust failure handling.
            Teams should test recovery paths and make errors observable.
            This article explains practical approaches for improving service
            resilience through monitoring, retries, and clear operational
            procedures.</p>
          </article></body>
        </html>
        """
        with patch(
            "app.services.url_digest._download_html",
            return_value=html,
        ):
            content = _extract_web_content("https://example.com/article")

        self.assertEqual(content.title, "Article About Reliable Systems")
        self.assertIn("robust failure handling", content.text)
        self.assertEqual(content.article_type, "article")


if __name__ == "__main__":
    unittest.main()
