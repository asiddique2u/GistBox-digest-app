from pydantic import BaseModel, HttpUrl

from app.services.agent.digest_models import DigestDetailLevel


class DigestRequest(BaseModel):
    url: HttpUrl
    detail_level: DigestDetailLevel = "medium"


class DigestResponse(BaseModel):
    url: HttpUrl
    detail_level: DigestDetailLevel
    title: str
    summary: str
