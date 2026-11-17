import logging
import os
from typing import Protocol

from openai import OpenAI

from .digest_models import (
    MAX_DIGEST_CONTENT_CHARS,
    DigestDetailLevel,
    DigestOutput,
)

logger = logging.getLogger(__name__)

PROMPT = """You are an expert analyst who creates faithful, useful digests of articles, tutorials, reviews, educational content, research, and videos.

Create a complete, informative digest that helps readers understand the source's important points and significance.

Guidelines:
- Create a compelling title (5-10 words) that captures the essence of the content
- For non-video sources, write the summary as Markdown bullets, not as a prose paragraph or a single sentence
- For videos, begin the summary with a brief overview paragraph explaining what the video is about and how it presents the subject, then follow with detailed content bullets
- Put distinct key points in separate bullets instead of combining them into one bullet
- Do not impose a word-count, sentence-count, or bullet-count limit; cover all important material
- Use the requested detail level to guide depth, not to cap the summary's size
- Adapt the structure to the source: use ordered steps with explanations for tutorials; identify reviewed products and report ratings only when the source provides them; list educational topics with a brief explanation of each; for research, include findings, methods, evidence, and limitations when available
- For other content, organize the key ideas, supporting details, and implications into clear bullets
- Focus on actionable insights and implications where relevant
- Use clear, accessible language while maintaining technical accuracy
- Avoid marketing fluff - focus on substance
- Do not invent details that are absent from the source
- Never invent product ratings, steps, topics, or supporting evidence
- Return only a JSON object with "title" and "summary" string fields"""

DEFAULT_PROVIDER_ORDER = ("openai", "gemini", "anthropic", "ollama", "openrouter")
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
PROVIDER_NAMES = frozenset(DEFAULT_PROVIDER_ORDER)
REQUEST_TIMEOUT_SECONDS = 30
DETAIL_GUIDANCE: dict[DigestDetailLevel, str] = {
    "short": "Prioritize the essential takeaways while retaining the details needed to understand them.",
    "medium": "Cover the main points and the important context and supporting details.",
    "detailed": "Thoroughly cover the important ideas, context, examples, steps, and supporting details.",
}


class DigestProvider(Protocol):
    name: str

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "detailed",
    ) -> DigestOutput: ...


def _detail_guidance(detail_level: DigestDetailLevel) -> str:
    try:
        return DETAIL_GUIDANCE[detail_level]
    except KeyError as exc:
        raise ValueError(f"Unsupported digest detail level: {detail_level}") from exc


def _user_prompt(
    title: str,
    content: str,
    article_type: str,
    detail_level: DigestDetailLevel,
) -> str:
    source = content[:MAX_DIGEST_CONTENT_CHARS]
    return (
        f"Create a digest for this {article_type}.\n"
        f"Title: {title}\n"
        f"Detail level: {detail_level}. {_detail_guidance(detail_level)}\n"
        "Include as many bullets as needed to cover the important material; "
        "do not shorten the digest to fit a target length.\n"
        f"Content:\n{source}"
    )


def _parse_digest(raw: str | None) -> DigestOutput:
    if not raw:
        raise ValueError("Provider returned an empty digest response")
    return DigestOutput.model_validate_json(raw)


class OpenAIDigestProvider:
    name = "openai"

    def __init__(
        self, api_key: str, model: str, base_url: str | None = None
    ) -> None:
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "detailed",
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


class OpenRouterDigestProvider(OpenAIDigestProvider):
    name = "openrouter"

    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://openrouter.ai/api/v1",
        )


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
        detail_level: DigestDetailLevel = "detailed",
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
        detail_level: DigestDetailLevel = "detailed",
    ) -> DigestOutput:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=64000,
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
            elif name == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY")
                if api_key:
                    providers.append(
                        OpenRouterDigestProvider(
                            api_key=api_key,
                            model=os.getenv(
                                "OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL
                            ),
                        )
                    )
        except ImportError:
            logger.exception(
                "Digest provider %s is configured but its SDK is unavailable", name
            )

    return providers
