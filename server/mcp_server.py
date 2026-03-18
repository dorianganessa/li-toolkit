"""MCP server exposing LinkedIn analytics to LLM clients."""

import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure local imports work when running standalone
sys.path.insert(0, str(Path(__file__).parent))

from analytics import compute_metrics  # noqa: E402
from database import PostRecord, SessionLocal, init_db  # noqa: E402
from strategy import load_strategy, save_strategy, suggest_strategy  # noqa: E402

mcp = FastMCP(
    "li-toolkit",
    description="Access your LinkedIn post history and analytics",
)


def _get_db():
    init_db()
    return SessionLocal()


@mcp.tool()
def get_post_analytics() -> str:
    """Get full analytics across all your LinkedIn posts.

    Returns aggregate metrics including engagement averages, distribution,
    top keywords, topic performance, timing analysis, and recommendations.
    """
    db = _get_db()
    try:
        metrics = compute_metrics(db)
        return json.dumps(metrics, default=str, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_posts(limit: int = 50, offset: int = 0) -> str:
    """Get your stored LinkedIn posts.

    Args:
        limit: Maximum number of posts to return (default 50).
        offset: Number of posts to skip for pagination.
    """
    db = _get_db()
    try:
        records = (
            db.query(PostRecord)
            .order_by(PostRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        posts = [
            {
                "id": r.id,
                "text": r.text,
                "likes": r.likes,
                "comments": r.comments,
                "reposts": r.reposts,
                "impressions": r.impressions,
                "published_at": str(r.published_at) if r.published_at else None,
            }
            for r in records
        ]
        return json.dumps(posts, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_top_posts(count: int = 5) -> str:
    """Get your best-performing LinkedIn posts ranked by engagement.

    Args:
        count: Number of top posts to return (default 5).
    """
    db = _get_db()
    try:
        records = db.query(PostRecord).all()
        posts = []
        for r in records:
            engagement = r.likes + r.comments * 2
            posts.append({
                "text": r.text,
                "likes": r.likes,
                "comments": r.comments,
                "reposts": r.reposts,
                "impressions": r.impressions,
                "engagement_score": engagement,
                "published_at": str(r.published_at) if r.published_at else None,
            })
        posts.sort(key=lambda p: p["engagement_score"], reverse=True)
        return json.dumps(posts[:count], indent=2)
    finally:
        db.close()


@mcp.tool()
def get_posting_recommendations() -> str:
    """Get data-driven recommendations for when, what, and how to post.

    Returns insights on best days, hours, topics, post length, and language
    based on your historical post performance.
    """
    db = _get_db()
    try:
        metrics = compute_metrics(db)
        if metrics.get("empty"):
            return json.dumps({"message": "No posts stored yet. Use the Chrome extension to collect your LinkedIn posts first."})

        return json.dumps({
            "recommendations": metrics.get("recommendations", []),
            "top_keywords": metrics.get("top_keywords", []),
            "topic_stats": metrics.get("topic_stats", []),
            "best_posts_for_reference": metrics.get("top_posts", [])[:3],
        }, default=str, indent=2)
    finally:
        db.close()


@mcp.tool()
def search_posts(query: str, limit: int = 20) -> str:
    """Search your LinkedIn posts by keyword.

    Args:
        query: Search term to look for in post text.
        limit: Maximum number of results (default 20).
    """
    db = _get_db()
    try:
        records = (
            db.query(PostRecord)
            .filter(PostRecord.text.contains(query))
            .order_by(PostRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        posts = [
            {
                "id": r.id,
                "text": r.text,
                "likes": r.likes,
                "comments": r.comments,
                "reposts": r.reposts,
                "impressions": r.impressions,
                "published_at": str(r.published_at) if r.published_at else None,
            }
            for r in records
        ]
        return json.dumps(posts, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_post_count() -> str:
    """Get the total number of LinkedIn posts stored."""
    db = _get_db()
    try:
        count = db.query(PostRecord).count()
        return json.dumps({"count": count})
    finally:
        db.close()


@mcp.tool()
def get_strategy() -> str:
    """Get your current LinkedIn content strategy.

    Returns your defined strategy (topics, audience, goals, tone, etc.)
    or an empty template with descriptions of each field if no strategy
    has been set up yet. Use this to understand what to ask the user
    when helping them define their strategy.
    """
    strategy = load_strategy()
    return json.dumps(strategy, indent=2)


@mcp.tool()
def update_strategy(
    topics: list[str] | None = None,
    audience: str | None = None,
    goals: str | None = None,
    frequency: str | None = None,
    tone: str | None = None,
    languages: list[str] | None = None,
    notes: str | None = None,
) -> str:
    """Update the user's LinkedIn content strategy.

    Call this to save strategy choices after discussing them with the user.
    Only provide the fields you want to update — others will be preserved.

    Args:
        topics: List of topics the user writes about. E.g., ["AI/ML", "Data Engineering", "Leadership"].
        audience: Who they're writing for. E.g., "Senior engineers and tech leads".
        goals: What they want to achieve. E.g., "Thought leadership and hiring".
        frequency: How often they want to post. E.g., "3 times per week".
        tone: Preferred writing style. E.g., "Conversational, direct, uses real examples".
        languages: Languages they post in. E.g., ["English", "Italian"].
        notes: Any additional context for AI assistants.
    """
    current = load_strategy()
    if topics is not None:
        current["topics"]["value"] = topics
    if audience is not None:
        current["audience"]["value"] = audience
    if goals is not None:
        current["goals"]["value"] = goals
    if frequency is not None:
        current["frequency"]["value"] = frequency
    if tone is not None:
        current["tone"]["value"] = tone
    if languages is not None:
        current["languages"]["value"] = languages
    if notes is not None:
        current["notes"]["value"] = notes

    saved = save_strategy(current)
    return json.dumps(saved, indent=2)


@mcp.tool()
def suggest_strategy_from_data() -> str:
    """Analyze your LinkedIn post history and suggest a content strategy.

    Use this as the first step when helping a user set up their strategy.
    It examines their actual post performance to suggest topics, timing,
    length, and language based on what has worked best for them.

    After getting suggestions, walk the user through each section,
    presenting the data-driven insights and asking for their input
    before saving with update_strategy.
    """
    db = _get_db()
    try:
        suggestions = suggest_strategy(db)
        return json.dumps(suggestions, default=str, indent=2)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
