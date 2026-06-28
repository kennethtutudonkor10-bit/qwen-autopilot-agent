"""Custom Qwen-Agent skills (tools) for the publishing pipeline."""
from .manuscript import (
    DraftListing,
    IngestManuscript,
    PublishBook,
    RunQualityChecks,
)

ALL_SKILLS = [IngestManuscript, DraftListing, RunQualityChecks, PublishBook]

__all__ = [
    "IngestManuscript",
    "DraftListing",
    "RunQualityChecks",
    "PublishBook",
    "ALL_SKILLS",
]
