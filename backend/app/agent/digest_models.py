from typing import Literal

from pydantic import BaseModel, Field

DigestDetailLevel = Literal["short", "medium", "detailed"]
MAX_DIGEST_CONTENT_CHARS = 8000


class DigestOutput(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
