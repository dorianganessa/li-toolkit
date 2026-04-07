"""Business logic layer — shared between REST API and MCP server."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from analytics import (
    _avg_readability,
    _build_post_data,
    _engagement_score,
    compute_metrics,
    compute_velocity,
    get_engagement_trend,
)
from database import PostRecord, PostSnapshot
from models import LinkedInPost
from readability import compute_readability
from strategy import load_strategy, save_strategy, suggest_strategy

# Posts younger than this are eligible for re-scraping
_RESCRAPE_AGE = timedelta(days=14)
# Minimum time between snapshots
_MIN_SNAPSHOT_INTERVAL = timedelta(hours=6)
# Maximum snapshots per post
_MAX_SNAPSHOTS = 10

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Raised when a service operation fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def save_posts(db: Session, posts: list[LinkedInPost]) -> dict:
    """Save new posts and update engagement on recent duplicates."""
    saved = 0
    duplicates = 0
    updated = 0
    now = datetime.utcnow()

    try:
        for post in posts:
            existing = (
                db.query(PostRecord)
                .filter(PostRecord.text_hash == post.text_hash)
                .first()
            )
            if existing:
                if _should_rescrape(existing, now):
                    _update_engagement(db, existing, post, now)
                    updated += 1
                else:
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
                last_scraped_at=now,
            )
            db.add(record)
            saved += 1

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Failed to save posts")
        raise ServiceError("Failed to save posts", status_code=500)

    return {
        "saved": saved,
        "duplicates": duplicates,
        "updated": updated,
        "total": len(posts),
    }


def _should_rescrape(record: PostRecord, now: datetime) -> bool:
    """Check if a post is eligible for re-scraping."""
    age = now - (record.created_at or now)
    if age > _RESCRAPE_AGE:
        return False
    if record.last_scraped_at:
        since_last = now - record.last_scraped_at
        if since_last < _MIN_SNAPSHOT_INTERVAL:
            return False
    return True


def _update_engagement(
    db: Session,
    record: PostRecord,
    post: LinkedInPost,
    now: datetime,
) -> None:
    """Update engagement numbers and create a snapshot."""
    # Check for edited post
    new_hash = hashlib.sha256(post.text.encode()).hexdigest()
    if new_hash != record.text_hash:
        record.text = post.text
        record.text_hash = new_hash
        record.edited = True

    # Create snapshot before updating (capture previous state)
    snapshot_count = (
        db.query(PostSnapshot)
        .filter(PostSnapshot.post_id == record.id)
        .count()
    )
    if snapshot_count < _MAX_SNAPSHOTS:
        db.add(PostSnapshot(
            post_id=record.id,
            likes=record.likes,
            comments=record.comments,
            reposts=record.reposts,
            impressions=record.impressions,
            scraped_at=record.last_scraped_at or record.created_at,
        ))

    # Update to new engagement numbers
    record.likes = post.likes
    record.comments = post.comments
    record.reposts = post.reposts
    record.impressions = post.impressions
    record.last_scraped_at = now
    if post.published_at and not record.published_at:
        record.published_at = post.published_at


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


def get_velocity(db: Session, post_id: int) -> dict:
    """Get engagement velocity for a specific post."""
    result = compute_velocity(db, post_id)
    if not result:
        return {
            "message": (
                "No velocity data. Post needs at least"
                " one re-scrape to track engagement changes."
            ),
        }
    return result


def get_recent_velocity(db: Session, count: int = 5) -> list[dict]:
    """Get velocity for the most recent posts that have snapshots."""
    from database import PostSnapshot

    post_ids = (
        db.query(PostSnapshot.post_id)
        .distinct()
        .order_by(PostSnapshot.post_id.desc())
        .limit(count)
        .all()
    )
    results = []
    for (pid,) in post_ids:
        v = compute_velocity(db, pid)
        if v:
            post = (
                db.query(PostRecord)
                .filter(PostRecord.id == pid)
                .first()
            )
            v["text_preview"] = (
                post.text[:100] + "..." if post and len(post.text) > 100
                else post.text if post else ""
            )
            results.append(v)
    return results


def get_trends(db: Session, days: int = 90) -> dict:
    """Get engagement trends over time."""
    weekly = get_engagement_trend(db, days=days)
    if not weekly:
        return {
            "has_data": False,
            "message": "Not enough data for trends.",
        }

    return {
        "has_data": True,
        "period_days": days,
        "weekly_engagement": weekly,
        "total_weeks": len(weekly),
    }


def get_strategy_suggestions(db: Session) -> dict:
    """Analyze post history and suggest a content strategy."""
    return suggest_strategy(db)
