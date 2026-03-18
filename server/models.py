"""Pydantic models for LinkedIn post data validation."""

import hashlib
from datetime import datetime

from pydantic import BaseModel, Field, computed_field


class LinkedInPost(BaseModel):
    """Schema for a single LinkedIn post received from the Chrome extension."""

    text: str = Field(max_length=100_000)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    reposts: int = Field(default=0, ge=0)
    impressions: int = Field(default=0, ge=0)
    published_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_hash(self) -> str:
        """SHA-256 hash of the post text, used for deduplication."""
        return hashlib.sha256(self.text.encode()).hexdigest()


class SaveResponse(BaseModel):
    """Response after saving posts."""

    saved: int
    duplicates: int
    total: int
