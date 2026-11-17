from pydantic import BaseModel, HttpUrl

from ..agent.digest_models import DigestDetailLevel


class DigestRequest(BaseModel):
    url: HttpUrl
    detail_level: DigestDetailLevel = "detailed"


class DigestResponse(BaseModel):
    url: HttpUrl
    detail_level: DigestDetailLevel
    title: str
    summary: str
