import logging
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .digest_models import (
    MAX_DIGEST_CONTENT_CHARS,
    DigestDetailLevel,
    DigestOutput,
)
from .digest_providers import (
    PROMPT,
    DigestProvider,
    build_digest_providers,
)

logger = logging.getLogger(__name__)
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"

__all__ = ["DigestAgent", "DigestOutput", "PROMPT"]


def _extractive_fallback_enabled() -> bool:
    value = os.getenv("DIGEST_EXTRACTIVE_FALLBACK", "true").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError("DIGEST_EXTRACTIVE_FALLBACK must be a boolean value")


def _extractive_digest(
    title: str,
    content: str,
) -> Optional[DigestOutput]:
    clean_content = " ".join(content[:MAX_DIGEST_CONTENT_CHARS].split())
    if not clean_content:
        return None

    sentences = re.split(r"(?<=[.!?])\s+", clean_content)
    summary = "\n".join(
        f"- {sentence.strip()}"
        for sentence in sentences
        if sentence.strip()
    )

    clean_title = " ".join(title.split()).strip()
    if not clean_title:
        clean_title = " ".join(clean_content.split()[:10])

    return DigestOutput(title=clean_title[:120], summary=summary)


class DigestAgent:
    def __init__(
        self,
        providers: Sequence[DigestProvider] | None = None,
        allow_extractive_fallback: bool | None = None,
    ) -> None:
        if providers is None:
            load_dotenv(dotenv_path=DOTENV_PATH)
            self.providers = build_digest_providers()
        else:
            self.providers = list(providers)
        if allow_extractive_fallback is None:
            allow_extractive_fallback = _extractive_fallback_enabled()
        self.allow_extractive_fallback = allow_extractive_fallback

    def generate_digest(
        self,
        title: str,
        content: str,
        article_type: str,
        detail_level: DigestDetailLevel = "detailed",
    ) -> Optional[DigestOutput]:
        for provider in self.providers:
            try:
                digest = provider.generate_digest(
                    title, content, article_type, detail_level
                )
                logger.info("Generated digest with %s provider", provider.name)
                return digest
            except Exception as exc:
                logger.warning(
                    "Digest provider %s failed (%s); trying next provider",
                    provider.name,
                    type(exc).__name__,
                )

        if self.allow_extractive_fallback:
            if self.providers:
                logger.warning(
                    "All configured AI providers failed; using extractive digest"
                )
            else:
                logger.warning(
                    "No AI providers are configured; using extractive digest"
                )
            return _extractive_digest(title, content)

        if self.providers:
            logger.error(
                "All configured AI providers failed and extractive fallback is disabled"
            )
        else:
            logger.error(
                "No AI providers are configured and extractive fallback is disabled"
            )
        return None

