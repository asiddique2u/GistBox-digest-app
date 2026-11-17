from datetime import datetime, timezone

from ..agent.digest_agent import DigestAgent
from ..agent.digest_models import DigestOutput
from .request_context import DigestRequestContext


class DigestGenerationError(RuntimeError):
    pass


def generate_digest_for_content(
    context: DigestRequestContext,
    title: str,
    text: str,
    article_type: str,
) -> DigestOutput:
    context.article_type = article_type
    context.title = title
    context.source_content = text
    digest = DigestAgent().generate_digest(
        title=title,
        content=text,
        article_type=article_type,
        detail_level=context.detail_level,
    )
    if digest is None:
        raise DigestGenerationError("Digest generation failed")
    context.digest = digest
    context.completed_at = datetime.now(timezone.utc)
    return digest
