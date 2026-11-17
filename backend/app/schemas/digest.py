from pydantic import BaseModel, HttpUrl, model_validator

from ..agent.digest_models import DigestDetailLevel


class DigestRequest(BaseModel):
    url: HttpUrl
    detail_level: DigestDetailLevel = "detailed"


class DigestResponse(BaseModel):
    url: HttpUrl | None = None
    filename: str | None = None
    detail_level: DigestDetailLevel
    title: str
    summary: str

    @model_validator(mode="after")
    def has_exactly_one_source(self) -> "DigestResponse":
        if (self.url is None) == (self.filename is None):
            raise ValueError("A digest response must include a URL or filename.")
        return self
