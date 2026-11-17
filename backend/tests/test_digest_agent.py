import unittest
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.app.agent import digest_agent
from backend.app.agent import digest_providers
from backend.app.agent.digest_agent import DigestAgent
from backend.app.agent.digest_models import DigestOutput
from backend.app.agent.digest_providers import (
    AnthropicDigestProvider,
    GeminiDigestProvider,
    OpenAIDigestProvider,
    OpenRouterDigestProvider,
)
from backend.app.agent.digest_models import DigestDetailLevel


class StubProvider:
    def __init__(self, name: str, result: DigestOutput | Exception) -> None:
        self.name = name
        self.result = result
        self.calls = 0
        self.detail_levels: list[DigestDetailLevel] = []

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "detailed",
    ) -> DigestOutput:
        self.calls += 1
        self.detail_levels.append(detail_level)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class DigestAgentTests(unittest.TestCase):
    def test_gemini_provider_uses_current_default_model(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "DIGEST_PROVIDER_ORDER": "gemini",
                    "GEMINI_API_KEY": "test-key",
                },
                clear=True,
            ),
            patch.object(digest_providers, "GeminiDigestProvider") as provider_class,
        ):
            digest_providers.build_digest_providers()

        provider_class.assert_called_once_with(
            api_key="test-key",
            model="gemini-3.5-flash-lite",
        )

    def test_openrouter_provider_uses_configured_key_and_model(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "DIGEST_PROVIDER_ORDER": "openrouter",
                    "OPENROUTER_API_KEY": "test-key",
                },
                clear=True,
            ),
            patch.object(
                digest_providers, "OpenRouterDigestProvider"
            ) as provider_class,
        ):
            digest_providers.build_digest_providers()

        provider_class.assert_called_once_with(
            api_key="test-key",
            model="openai/gpt-4o-mini",
        )

    def test_openrouter_provider_uses_openrouter_api_endpoint(self) -> None:
        with patch("backend.app.agent.digest_providers.OpenAI") as openai:
            OpenRouterDigestProvider("test-key", "test-model")

        openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            timeout=digest_providers.REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def test_prompt_requests_content_aware_bullets_without_length_target(self) -> None:
        prompt = digest_providers._user_prompt(
            "Source", "Content.", "tutorial", "detailed"
        )

        self.assertIn("Markdown bullets", digest_providers.PROMPT)
        self.assertIn("ordered steps", digest_providers.PROMPT)
        self.assertIn("reviewed products", digest_providers.PROMPT)
        self.assertIn("educational topics", digest_providers.PROMPT)
        self.assertIn("do not shorten the digest to fit a target length", prompt)
        self.assertNotIn("word count", prompt.lower())

    def test_video_prompt_starts_with_overview_before_detail_bullets(self) -> None:
        self.assertIn(
            "begin the summary with a brief overview paragraph",
            digest_providers.PROMPT,
        )
        self.assertIn(
            "then follow with detailed content bullets",
            digest_providers.PROMPT,
        )

    def test_loads_backend_dotenv_before_building_providers(self) -> None:
        self.assertEqual(
            digest_agent.DOTENV_PATH,
            digest_agent.Path(digest_agent.__file__).resolve().parents[1] / ".env",
        )
        with (
            patch.object(digest_agent, "load_dotenv") as load_dotenv,
            patch.object(
                digest_agent, "build_digest_providers", return_value=[]
            ) as build_providers,
        ):
            DigestAgent()

        load_dotenv.assert_called_once_with(dotenv_path=digest_agent.DOTENV_PATH)
        build_providers.assert_called_once_with()

    def test_tries_next_provider_after_failure(self) -> None:
        unavailable = StubProvider("primary", RuntimeError("unavailable"))
        backup_result = DigestOutput(title="Backup Digest", summary="Useful summary.")
        backup = StubProvider("backup", backup_result)
        agent = DigestAgent(
            providers=[unavailable, backup],
            allow_extractive_fallback=False,
        )

        with self.assertLogs("backend.app.agent.digest_agent", level="WARNING"):
            result = agent.generate_digest("Article", "Article content.", "article")

        self.assertEqual(result, backup_result)
        self.assertEqual(unavailable.calls, 1)
        self.assertEqual(backup.calls, 1)

    def test_uses_extractive_fallback_when_all_providers_fail(self) -> None:
        provider = StubProvider("primary", RuntimeError("unavailable"))
        agent = DigestAgent(providers=[provider], allow_extractive_fallback=True)
        content = " ".join(
            f"Sentence {index} contains key information."
            for index in range(20)
        )

        with self.assertLogs("backend.app.agent.digest_agent", level="WARNING"):
            result = agent.generate_digest(
                "  Original   Article ",
                content,
                "article",
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Original Article")
        self.assertTrue(
            all(line.startswith("- ") for line in result.summary.splitlines())
        )
        self.assertEqual(len(result.summary.splitlines()), 20)

    def test_accepts_concise_ai_summary_without_retrying(self) -> None:
        content = " ".join(
            f"Sentence {index} contains key information."
            for index in range(20)
        )
        short_result = DigestOutput(title="Short", summary="Useful shorter summary.")
        provider = StubProvider("primary", short_result)
        backup = StubProvider(
            "backup",
            DigestOutput(title="Backup", summary="This should not be used."),
        )
        agent = DigestAgent(
            providers=[provider, backup],
            allow_extractive_fallback=True,
        )

        result = agent.generate_digest(
            "Article",
            content,
            "article",
            detail_level="medium",
        )

        self.assertEqual(result, short_result)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(backup.calls, 0)
        self.assertEqual(provider.detail_levels, ["medium"])

    def test_passes_selected_detail_level_to_provider(self) -> None:
        content = " ".join(["word"] * 100)
        summary = " ".join(["detail"] * 30)
        result = DigestOutput(title="Detailed", summary=summary)
        provider = StubProvider("primary", result)
        agent = DigestAgent(providers=[provider], allow_extractive_fallback=False)

        digest = agent.generate_digest(
            "Article", content, "article", detail_level="detailed"
        )

        self.assertEqual(digest, result)
        self.assertEqual(provider.detail_levels, ["detailed"])

    def test_defaults_to_detailed_digest(self) -> None:
        provider = StubProvider(
            "primary",
            DigestOutput(title="Detailed", summary="- Key details."),
        )
        agent = DigestAgent(providers=[provider], allow_extractive_fallback=False)

        agent.generate_digest("Article", "Content.", "article")

        self.assertEqual(provider.detail_levels, ["detailed"])

    def test_openai_provider_parses_structured_response(self) -> None:
        provider = OpenAIDigestProvider("test-key", "test-model")
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"title":"OpenAI digest","summary":"Summary."}'
                    )
                )
            ]
        )
        with patch.object(
            provider.client.chat.completions, "create", return_value=response
        ) as create:
            result = provider.generate_digest("Article", "Content.", "article")

        self.assertEqual(result.title, "OpenAI digest")
        create.assert_called_once()

    def test_gemini_provider_parses_structured_response(self) -> None:
        provider = GeminiDigestProvider("test-key", "test-model")
        response = SimpleNamespace(
            output_text='{"title":"Gemini digest","summary":"Summary."}'
        )
        with patch.object(
            provider.client.interactions, "create", return_value=response
        ) as create:
            result = provider.generate_digest("Article", "Content.", "article")

        self.assertEqual(result.title, "Gemini digest")
        create.assert_called_once()

    def test_anthropic_provider_parses_text_response(self) -> None:
        provider = AnthropicDigestProvider("test-key", "test-model")
        response = SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="text",
                    text='{"title":"Claude digest","summary":"Summary."}',
                )
            ]
        )
        with patch.object(
            provider.client.messages, "create", return_value=response
        ) as create:
            result = provider.generate_digest("Article", "Content.", "article")

        self.assertEqual(result.title, "Claude digest")
        create.assert_called_once()

    def test_returns_none_for_empty_content_without_ai_providers(self) -> None:
        agent = DigestAgent(providers=[], allow_extractive_fallback=True)

        with self.assertLogs("backend.app.agent.digest_agent", level="WARNING"):
            result = agent.generate_digest("Article", "  ", "article")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
