import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from backend.app.agent.digest_models import DigestOutput
from app.extraction.youtube import TranscriptFetchError
from app.services.request_context import DigestRequestContext
from app.services.url_digest import (
    ExtractedContent,
    UnsafeURL,
    URLFetchError,
    _download_html,
    _extract_youtube_content,
    _extract_web_content,
    _validate_public_url,
    process_digest_request,
)


client = TestClient(app)


class URLDigestTests(unittest.TestCase):
    def test_digest_request_context_collects_source_data(self) -> None:
        context = DigestRequestContext(
            url="https://example.com/article",
            detail_level="medium",
        )
        extracted = ExtractedContent(
            title="A Useful Article",
            text="The article source text.",
            article_type="article",
        )
        digest = DigestOutput(title="A Useful Digest", summary="Key points.")

        with (
            patch(
                "app.services.url_digest._validate_public_url",
                return_value=("example.com", 443),
            ),
            patch(
                "app.services.url_digest._extract_web_content",
                return_value=extracted,
            ),
            patch("app.services.content_digest.DigestAgent") as agent_class,
        ):
            agent_class.return_value.generate_digest.return_value = digest
            result = process_digest_request(context)

        self.assertEqual(result, digest)
        self.assertEqual(context.article_type, "article")
        self.assertEqual(context.title, "A Useful Article")
        self.assertEqual(context.source_content, "The article source text.")
        self.assertEqual(context.digest, digest)
        self.assertIsNotNone(context.completed_at)
        agent_class.return_value.generate_digest.assert_called_once_with(
            title="A Useful Article",
            content="The article source text.",
            article_type="article",
            detail_level="medium",
        )

    def test_digest_request_context_captures_youtube_transcript(self) -> None:
        context = DigestRequestContext(
            url="https://youtube.com/watch?v=abcdefghijk",
            detail_level="short",
        )
        extracted = ExtractedContent(
            title="A Video",
            text="The video transcript.",
            article_type="youtube",
        )
        digest = DigestOutput(title="A Video Digest", summary="Key points.")

        with (
            patch(
                "app.services.url_digest._validate_public_url",
                return_value=("youtube.com", 443),
            ),
            patch(
                "app.services.url_digest._extract_youtube_content",
                return_value=extracted,
            ),
            patch("app.services.content_digest.DigestAgent") as agent_class,
        ):
            agent_class.return_value.generate_digest.return_value = digest
            process_digest_request(context)

        self.assertEqual(context.article_type, "youtube")
        self.assertEqual(context.source_content, "The video transcript.")
        self.assertIsNotNone(context.request_id)
        self.assertIsNotNone(context.received_at)

    def test_youtube_transcript_fetch_error_is_reported_as_upstream_failure(
        self,
    ) -> None:
        with patch(
            "app.services.url_digest.YouTubeScraper"
        ) as scraper_class:
            scraper_class.return_value.get_transcript.side_effect = (
                TranscriptFetchError("upstream failure")
            )
            with self.assertRaises(URLFetchError):
                _extract_youtube_content(
                    "https://youtube.com/watch?v=abcdefghijk",
                    "youtube.com",
                )

    def test_post_digest_maps_transcript_fetch_error_to_bad_gateway(self) -> None:
        with patch(
            "main.process_digest_request",
            side_effect=URLFetchError(
                "The YouTube transcript service could not retrieve captions"
            ),
        ):
            response = client.post(
                "/digest",
                json={"url": "https://youtube.com/watch?v=abcdefghijk"},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"],
            "The YouTube transcript service could not retrieve captions",
        )

    def test_post_digest_returns_requested_detail_level(self) -> None:
        digest = DigestOutput(title="A Useful Digest", summary="Key points.")

        def generate(context: DigestRequestContext) -> DigestOutput:
            self.assertEqual(context.url, "https://example.com/article")
            self.assertEqual(context.detail_level, "detailed")
            context.title = digest.title
            context.source_content = "The source text."
            context.digest = digest
            return digest

        with patch("main.process_digest_request", side_effect=generate) as process:
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
        process.assert_called_once()
        context = process.call_args.args[0]
        self.assertEqual(context.url, "")
        self.assertIsNone(context.request_id)
        self.assertIsNone(context.received_at)
        self.assertIsNone(context.completed_at)
        self.assertIsNone(context.article_type)
        self.assertIsNone(context.title)
        self.assertIsNone(context.source_content)
        self.assertIsNone(context.digest)

    def test_post_digest_defaults_to_detailed(self) -> None:
        digest = DigestOutput(title="A Useful Digest", summary="Key points.")
        with patch("main.process_digest_request", return_value=digest) as process:
            response = client.post(
                "/digest",
                json={"url": "https://example.com/article"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail_level"], "detailed")
        process.assert_called_once()
        self.assertEqual(
            process.call_args.args[0].detail_level,
            "detailed",
        )

    def test_post_digest_rejects_unknown_detail_level(self) -> None:
        with patch("main.process_digest_request") as process:
            response = client.post(
                "/digest",
                json={
                    "url": "https://example.com/article",
                    "detail_level": "extra-long",
                },
            )

        self.assertEqual(response.status_code, 422)
        process.assert_not_called()

    def test_post_digest_rejects_non_http_urls(self) -> None:
        with patch("main.process_digest_request") as process:
            response = client.post("/digest", json={"url": "file:///etc/passwd"})

        self.assertEqual(response.status_code, 422)
        process.assert_not_called()

    def test_post_digest_maps_unsafe_url_to_client_error(self) -> None:
        context = DigestRequestContext(
            url="https://example.com/article",
            detail_level="detailed",
        )
        with patch(
            "main.DigestRequestContext",
            return_value=context,
        ), patch(
            "main.process_digest_request",
            side_effect=UnsafeURL("The URL must resolve to a public internet address"),
        ):
            response = client.post(
                "/digest",
                json={"url": "https://example.com/article"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(context.url, "")
        self.assertIsNone(context.request_id)

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
