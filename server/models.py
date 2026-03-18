"""Pydantic models for LinkedIn post data validation."""

import hashlib
from datetime import datetime

from pydantic import BaseModel, computed_field


class LinkedInPost(BaseModel):
    """Schema for a single LinkedIn post received from the Chrome extension."""

    text: str
    likes: int
    comments: int
    reposts: int = 0
    impressions: int = 0
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
