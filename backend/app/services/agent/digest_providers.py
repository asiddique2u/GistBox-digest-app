import logging
import os
from typing import Protocol

from openai import OpenAI

from .digest_models import (
    DIGEST_LENGTH_RATIOS,
    MAX_DIGEST_CONTENT_CHARS,
    DigestDetailLevel,
    DigestOutput,
    summary_word_range,
)

logger = logging.getLogger(__name__)

PROMPT = """You are an expert AI news analyst specializing in summarizing technical articles, research papers, and video content about artificial intelligence.

Create a faithful, informative digest that helps readers understand the key points and significance of the content.

Guidelines:
- Create a compelling title (5-10 words) that captures the essence of the content
- Use the requested detail level and word range as soft guidance, not a strict limit
- Prioritize a useful, coherent summary over matching an exact word count
- Focus on actionable insights and implications
- Use clear, accessible language while maintaining technical accuracy
- Avoid marketing fluff - focus on substance
- Do not invent details that are absent from the source
- Return only a JSON object with "title" and "summary" string fields"""

DEFAULT_PROVIDER_ORDER = ("openai", "gemini", "anthropic", "ollama")
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
PROVIDER_NAMES = frozenset(DEFAULT_PROVIDER_ORDER)
REQUEST_TIMEOUT_SECONDS = 30
SENTENCE_GUIDANCE: dict[DigestDetailLevel, str] = {
    "short": "about 2-4 sentences",
    "medium": "about 4-8 sentences",
    "detailed": "about 8-12 sentences",
}


class DigestProvider(Protocol):
    name: str

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "medium",
    ) -> DigestOutput: ...


def _user_prompt(
    title: str,
    content: str,
    article_type: str,
    detail_level: DigestDetailLevel,
) -> str:
    source = content[:MAX_DIGEST_CONTENT_CHARS]
    minimum_words, maximum_words = summary_word_range(source, detail_level)
    minimum_ratio, maximum_ratio = DIGEST_LENGTH_RATIOS[detail_level]
    return (
        f"Create a digest for this {article_type}.\n"
        f"Title: {title}\n"
        f"Detail level: {detail_level}; target {SENTENCE_GUIDANCE[detail_level]}.\n"
        f"Aim for {minimum_words}-{maximum_words} words, "
        f"approximately {minimum_ratio:.0%}-{maximum_ratio:.0%} of the "
        f"{len(source.split())}-word source text. This is a soft target; "
        "prioritize a useful, coherent summary over hitting the exact word "
        "count. The summary word count does not include the title.\n"
        f"Content:\n{source}"
    )


def _parse_digest(raw: str | None) -> DigestOutput:
    if not raw:
        raise ValueError("Provider returned an empty digest response")
    return DigestOutput.model_validate_json(raw)


class OpenAIDigestProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "medium",
    ) -> DigestOutput:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": PROMPT},
                {
                    "role": "user",
                    "content": _user_prompt(
                        title, content, article_type, detail_level
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        return _parse_digest(response.choices[0].message.content)


class OllamaDigestProvider(OpenAIDigestProvider):
    name = "ollama"

    def __init__(self, model: str, base_url: str) -> None:
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
            base_url=base_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )


class GeminiDigestProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        self.model = model
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_SECONDS * 1000
            ),
        )

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "medium",
    ) -> DigestOutput:
        response = self.client.interactions.create(
            model=self.model,
            input=(
                f"{PROMPT}\n\n"
                f"{_user_prompt(title, content, article_type, detail_level)}"
            ),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": DigestOutput.model_json_schema(),
            },
        )
        return _parse_digest(response.output_text)


class AnthropicDigestProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str) -> None:
        from anthropic import Anthropic

        self.model = model
        self.client = Anthropic(
            api_key=api_key,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "medium",
    ) -> DigestOutput:
        _, maximum_words = summary_word_range(
            content[:MAX_DIGEST_CONTENT_CHARS], detail_level
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max(512, maximum_words * 2 + 128),
            system=PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _user_prompt(
                        title, content, article_type, detail_level
                    ),
                }
            ],
        )
        text = next(
            (block.text for block in response.content if block.type == "text"),
            None,
        )
        return _parse_digest(text)


def build_digest_providers() -> list[DigestProvider]:
    configured_order = os.getenv(
        "DIGEST_PROVIDER_ORDER", ",".join(DEFAULT_PROVIDER_ORDER)
    )
    provider_order = [name.strip().lower() for name in configured_order.split(",")]
    if not provider_order or any(not name for name in provider_order):
        raise ValueError("DIGEST_PROVIDER_ORDER must be a comma-separated provider list")
    if len(provider_order) != len(set(provider_order)):
        raise ValueError("DIGEST_PROVIDER_ORDER cannot contain duplicate providers")
    unknown_providers = set(provider_order) - PROVIDER_NAMES
    if unknown_providers:
        raise ValueError(
            "Unsupported digest provider(s): "
            + ", ".join(sorted(unknown_providers))
        )

    providers: list[DigestProvider] = []
    for name in provider_order:
        try:
            if name == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    providers.append(
                        OpenAIDigestProvider(
                            api_key=api_key,
                            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        )
                    )
            elif name == "gemini":
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if api_key:
                    providers.append(
                        GeminiDigestProvider(
                            api_key=api_key,
                            model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
                        )
                    )
            elif name == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    providers.append(
                        AnthropicDigestProvider(
                            api_key=api_key,
                            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
                        )
                    )
            elif name == "ollama":
                model = os.getenv("OLLAMA_MODEL")
                if model:
                    providers.append(
                        OllamaDigestProvider(
                            model=model,
                            base_url=os.getenv(
                                "OLLAMA_BASE_URL", "http://localhost:11434/v1"
                            ),
                        )
                    )
        except ImportError:
            logger.exception(
                "Digest provider %s is configured but its SDK is unavailable", name
            )

    return providers
