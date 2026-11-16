import unittest
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.agent import digest_agent
from app.services.agent import digest_providers
from app.services.agent.digest_agent import DigestAgent
from app.services.agent.digest_models import DigestOutput
from app.services.agent.digest_providers import (
    AnthropicDigestProvider,
    GeminiDigestProvider,
    OpenAIDigestProvider,
)
from app.services.agent.digest_models import DigestDetailLevel, summary_word_range


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
        detail_level: DigestDetailLevel = "medium",
    ) -> DigestOutput:
        self.calls += 1
        self.detail_levels.append(detail_level)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class DigestAgentTests(unittest.TestCase):
    def test_summary_word_ranges_match_detail_levels(self) -> None:
        content = " ".join(["word"] * 1000)

        self.assertEqual(summary_word_range(content, "short"), (50, 100))
        self.assertEqual(summary_word_range(content, "medium"), (150, 250))
        self.assertEqual(summary_word_range(content, "detailed"), (250, 350))

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

    def test_loads_backend_dotenv_before_building_providers(self) -> None:
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

        with self.assertLogs("app.services.agent.digest_agent", level="WARNING"):
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

        with self.assertLogs("app.services.agent.digest_agent", level="WARNING"):
            result = agent.generate_digest(
                "  Original   Article ",
                content,
                "article",
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Original Article")
        self.assertGreaterEqual(len(result.summary.split()), 15)

    def test_accepts_ai_summary_below_requested_minimum(self) -> None:
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

        with self.assertLogs("app.services.agent.digest_agent", level="WARNING"):
            result = agent.generate_digest("Article", "  ", "article")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
