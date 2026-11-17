from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..agent.digest_models import DigestDetailLevel, DigestOutput


@dataclass(slots=True)
class DigestRequestContext:
    url: str
    detail_level: DigestDetailLevel
    request_id: UUID | None = field(default_factory=uuid4)
    received_at: datetime | None = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    article_type: str | None = None
    title: str | None = None
    source_content: str | None = field(default=None, repr=False)
    digest: DigestOutput | None = field(default=None, repr=False)

    def clear(self) -> None:
        self.url = ""
        self.detail_level = "detailed"
        self.request_id = None
        self.received_at = None
        self.completed_at = None
        self.article_type = None
        self.title = None
        self.source_content = None
        self.digest = None
