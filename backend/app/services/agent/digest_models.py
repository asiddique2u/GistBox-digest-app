from math import ceil
from typing import Literal

from pydantic import BaseModel, Field

DigestDetailLevel = Literal["short", "medium", "detailed"]
MAX_DIGEST_CONTENT_CHARS = 8000
DIGEST_LENGTH_RATIOS: dict[DigestDetailLevel, tuple[float, float]] = {
    "short": (0.05, 0.10),
    "medium": (0.15, 0.25),
    "detailed": (0.25, 0.35),
}


class DigestOutput(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)


def summary_word_range(
    content: str, detail_level: DigestDetailLevel
) -> tuple[int, int]:
    if detail_level not in DIGEST_LENGTH_RATIOS:
        raise ValueError(f"Unsupported digest detail level: {detail_level}")

    source_word_count = len(content[:MAX_DIGEST_CONTENT_CHARS].split())
    if not source_word_count:
        return 0, 0

    minimum_ratio, maximum_ratio = DIGEST_LENGTH_RATIOS[detail_level]
    return (
        ceil(source_word_count * minimum_ratio),
        ceil(source_word_count * maximum_ratio),
    )
