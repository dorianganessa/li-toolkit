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
    post_type: str | None = None
    hashtags: list[str] | None = None
    has_link: bool | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text_hash(self) -> str:
        """SHA-256 hash of the post text, used for deduplication."""
        return hashlib.sha256(self.text.encode()).hexdigest()


class SaveResponse(BaseModel):
    """Response after saving posts."""

    saved: int
    duplicates: int
    updated: int = 0
    total: int


# ---------------------------------------------------------------------------
# Response models — used by REST API and CLI
# ---------------------------------------------------------------------------


class PostSummary(BaseModel):
    """A post with basic fields."""

    id: int
    text: str
    likes: int
    comments: int
    reposts: int
    impressions: int
    published_at: str | None = None
    created_at: str | None = None
    post_type: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    has_link: bool | None = None


class TopPostSummary(BaseModel):
    """A top post with engagement score."""

    text: str
    likes: int
    comments: int
    reposts: int
    impressions: int
    engagement_score: int
    published_at: str | None = None


class PostCountResponse(BaseModel):
    """Total number of stored posts."""

    count: int


class ReadabilityMetrics(BaseModel):
    """Readability metrics for a single text."""

    flesch_kincaid_grade: float = 0.0
    avg_sentence_length: float = 0.0
    vocab_richness: float = 0.0
    emoji_density: float = 0.0
    hashtag_count: int = 0
    word_count: int = 0


class AvgReadability(BaseModel):
    """Average readability across multiple posts."""

    avg_flesch_kincaid: float = 0.0
    avg_sentence_length: float = 0.0
    avg_vocab_richness: float = 0.0
    avg_word_count: float = 0.0


class LengthBucket(BaseModel):
    label: str
    range: str
    count: int
    avg_engagement: float
    avg_likes: float = 0.0
    avg_impressions: float = 0.0


class LanguageStat(BaseModel):
    language: str
    count: int
    avg_engagement: float
    avg_impressions: float = 0.0


class KeywordStat(BaseModel):
    keyword: str
    count: int
    avg_engagement: float
    total_engagement: int


class DayOfWeekStat(BaseModel):
    day: str
    count: int
    avg_engagement: float


class HourStat(BaseModel):
    hour: str
    count: int
    avg_engagement: float


class TopicStat(BaseModel):
    topic: str
    count: int
    avg_engagement: float
    avg_likes: float = 0.0
    avg_impressions: float = 0.0
    avg_engagement_rate: float = 0.0


class PostTypeStat(BaseModel):
    post_type: str
    count: int
    avg_engagement: float
    avg_impressions: float = 0.0


class ReadabilityBucket(BaseModel):
    label: str
    range: str | None = None
    count: int
    avg_engagement: float


class EmojiBucket(BaseModel):
    label: str
    count: int
    avg_engagement: float


class Recommendation(BaseModel):
    type: str
    label: str
    value: str
    detail: str


class EngagementDistribution(BaseModel):
    """Engagement distribution buckets."""

    zero: int = Field(default=0, alias="0")
    low: int = Field(default=0, alias="1-10")
    medium: int = Field(default=0, alias="11-50")
    high: int = Field(default=0, alias="51-100")
    very_high: int = Field(default=0, alias="101-500")
    viral: int = Field(default=0, alias="500+")

    model_config = {"populate_by_name": True}


class AnalyticsResponse(BaseModel):
    """Full analytics response."""

    empty: bool
    total_posts: int | None = None
    avg_engagement: float | None = None
    avg_likes: float | None = None
    avg_comments: float | None = None
    avg_impressions: int | None = None
    avg_engagement_rate: float | None = None
    engagement_distribution: dict | None = None
    length_analysis: list[LengthBucket] | None = None
    language_analysis: list[LanguageStat] | None = None
    top_keywords: list[KeywordStat] | None = None
    has_temporal_data: bool | None = None
    posts_with_dates: int | None = None
    day_of_week_stats: list[DayOfWeekStat] | None = None
    hour_stats: list[HourStat] | None = None
    topic_stats: list[TopicStat] | None = None
    post_type_stats: list[PostTypeStat] | None = None
    readability_vs_engagement: list[ReadabilityBucket] | None = None
    emoji_vs_engagement: list[EmojiBucket] | None = None
    avg_readability: AvgReadability | None = None
    recommendations: list[Recommendation] | None = None
    top_posts: list[dict] | None = None
    bottom_posts: list[dict] | None = None


class RecommendationsResponse(BaseModel):
    """Posting recommendations response."""

    message: str | None = None
    recommendations: list | None = None
    top_keywords: list | None = None
    topic_stats: list | None = None
    best_posts_for_reference: list | None = None


class DraftAnalysisResponse(BaseModel):
    """Draft analysis response."""

    draft: dict
    your_averages: dict | None = None
    your_top_posts_averages: dict | None = None
    comparison: str


class VelocityInterval(BaseModel):
    from_time: str = Field(alias="from")
    to: str
    hours: float
    engagement_delta: int
    likes_delta: int
    comments_delta: int
    engagement_per_hour: float

    model_config = {"populate_by_name": True}


class VelocityResponse(BaseModel):
    """Engagement velocity response."""

    message: str | None = None
    post_id: int | None = None
    snapshots: int | None = None
    intervals: list | None = None
    total_engagement_gained: int | None = None
    total_hours: float | None = None
    avg_engagement_per_hour: float | None = None
    trajectory: str | None = None
    text_preview: str | None = None


class TrendsWeek(BaseModel):
    week: str
    posts: int
    avg_engagement: float
    total_engagement: int


class TrendsResponse(BaseModel):
    """Engagement trends response."""

    has_data: bool = False
    message: str | None = None
    period_days: int | None = None
    weekly_engagement: list[TrendsWeek] | None = None
    total_weeks: int | None = None
