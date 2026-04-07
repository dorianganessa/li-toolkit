"""Business logic layer — shared between REST API and MCP server."""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from analytics import (
    _avg_readability,
    _build_post_data,
    _engagement_score,
    compute_metrics,
)
from database import PostRecord
from models import LinkedInPost
from readability import compute_readability
from strategy import load_strategy, save_strategy, suggest_strategy

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when a service operation fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def save_posts(db: Session, posts: list[LinkedInPost]) -> dict:
    """Save posts, skipping duplicates. Returns counts."""
    saved = 0
    duplicates = 0

    try:
        for post in posts:
            exists = (
                db.query(PostRecord)
                .filter(PostRecord.text_hash == post.text_hash)
                .first()
            )
            if exists:
                duplicates += 1
                continue

            record = PostRecord(
                text_hash=post.text_hash,
                text=post.text,
                likes=post.likes,
                comments=post.comments,
                reposts=post.reposts,
                impressions=post.impressions,
                published_at=post.published_at,
            )
            db.add(record)
            saved += 1

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to save posts")
        raise ServiceError("Failed to save posts", status_code=500)

    return {"saved": saved, "duplicates": duplicates, "total": len(posts)}


def list_posts(
    db: Session, limit: int = 100, offset: int = 0,
) -> list[dict]:
    """Return posts ordered by creation date descending."""
    records = (
        db.query(PostRecord)
        .order_by(PostRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "likes": r.likes,
            "comments": r.comments,
            "reposts": r.reposts,
            "impressions": r.impressions,
            "published_at": (
                str(r.published_at) if r.published_at else None
            ),
            "created_at": str(r.created_at),
        }
        for r in records
    ]


def get_post_count(db: Session) -> int:
    """Return total number of stored posts."""
    return db.query(PostRecord).count()


def get_analytics(db: Session) -> dict:
    """Compute full analytics across all stored posts."""
    custom_topics = _load_custom_topics()
    return compute_metrics(db, custom_topics=custom_topics)


def _load_custom_topics() -> dict | None:
    """Load custom topic clusters from strategy, if any."""
    strategy = load_strategy()
    ct = strategy.get("custom_topics", {})
    value = ct.get("value", {}) if isinstance(ct, dict) else {}
    return value if value else None


def search_posts(
    db: Session, query: str, limit: int = 20,
) -> list[dict]:
    """Search posts by keyword in text."""
    records = (
        db.query(PostRecord)
        .filter(PostRecord.text.contains(query))
        .order_by(PostRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "likes": r.likes,
            "comments": r.comments,
            "reposts": r.reposts,
            "impressions": r.impressions,
            "published_at": (
                str(r.published_at) if r.published_at else None
            ),
        }
        for r in records
    ]


def get_top_posts(db: Session, count: int = 5) -> list[dict]:
    """Return top posts ranked by engagement score."""
    records = db.query(PostRecord).all()
    posts = []
    for r in records:
        engagement = _engagement_score(r.likes, r.comments, r.reposts)
        posts.append({
            "text": r.text,
            "likes": r.likes,
            "comments": r.comments,
            "reposts": r.reposts,
            "impressions": r.impressions,
            "engagement_score": engagement,
            "published_at": (
                str(r.published_at) if r.published_at else None
            ),
        })
    posts.sort(key=lambda p: p["engagement_score"], reverse=True)
    return posts[:count]


def get_recommendations(db: Session) -> dict:
    """Return posting recommendations based on historical data."""
    metrics = get_analytics(db)
    if metrics.get("empty"):
        return {
            "message": (
                "No posts stored yet. Use the Chrome"
                " extension to collect your LinkedIn"
                " posts first."
            ),
        }
    return {
        "recommendations": metrics.get("recommendations", []),
        "top_keywords": metrics.get("top_keywords", []),
        "topic_stats": metrics.get("topic_stats", []),
        "best_posts_for_reference": metrics.get("top_posts", [])[:3],
    }


def get_strategy() -> dict:
    """Load the current content strategy."""
    return load_strategy()


def update_strategy_fields(
    topics: list[str] | None = None,
    audience: str | None = None,
    goals: str | None = None,
    frequency: str | None = None,
    tone: str | None = None,
    languages: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """Update specific strategy fields, preserving others."""
    current = load_strategy()
    field_map = {
        "topics": topics,
        "audience": audience,
        "goals": goals,
        "frequency": frequency,
        "tone": tone,
        "languages": languages,
        "notes": notes,
    }
    for field, value in field_map.items():
        if value is not None:
            current[field]["value"] = value
    return save_strategy(current)


def analyze_draft(db: Session, text: str) -> dict:
    """Analyze a draft post's readability against historical performance."""
    draft_metrics = compute_readability(text)
    draft_metrics["char_count"] = len(text)

    records = db.query(PostRecord).all()
    if not records:
        return {
            "draft": draft_metrics,
            "your_averages": None,
            "your_top_posts_averages": None,
            "comparison": "No historical data yet. Collect posts first.",
        }

    posts = _build_post_data(records)
    all_avg = _avg_readability(posts)

    top_posts = sorted(posts, key=lambda p: p["engagement"], reverse=True)
    top_n = top_posts[: max(len(top_posts) // 5, 3)]
    top_avg = _avg_readability(top_n)

    comparisons = []
    if draft_metrics["flesch_kincaid_grade"] < all_avg.get("avg_flesch_kincaid", 0):
        comparisons.append("Your draft is more readable than your average post")
    elif draft_metrics["flesch_kincaid_grade"] > all_avg.get("avg_flesch_kincaid", 0):
        comparisons.append("Your draft is less readable than your average post")

    if draft_metrics["word_count"] > all_avg.get("avg_word_count", 0) * 1.5:
        comparisons.append("Your draft is significantly longer than your average post")
    elif draft_metrics["word_count"] < all_avg.get("avg_word_count", 0) * 0.5:
        comparisons.append("Your draft is significantly shorter than your average post")

    return {
        "draft": draft_metrics,
        "your_averages": all_avg,
        "your_top_posts_averages": top_avg,
        "comparison": (
            ". ".join(comparisons)
            if comparisons
            else "Metrics are close to your averages"
        ),
    }


def get_strategy_suggestions(db: Session) -> dict:
    """Analyze post history and suggest a content strategy."""
    return suggest_strategy(db)
