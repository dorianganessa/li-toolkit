"""MCP server exposing LinkedIn analytics to LLM clients."""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure local imports work when running standalone
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, init_db  # noqa: E402
from services import (  # noqa: E402
    analyze_draft as svc_analyze_draft,
)
from services import (  # noqa: E402
    get_analytics,
    get_post_count,
    get_recent_velocity,
    get_recommendations,
    get_strategy,
    get_strategy_suggestions,
    get_top_posts,
    get_velocity,
    list_posts,
    search_posts,
    update_strategy_fields,
)
from services import (  # noqa: E402
    get_trends as svc_get_trends,
)

mcp = FastMCP(
    "li-toolkit",
    instructions="Access your LinkedIn post history and analytics",
)

# Initialize the database once at import time
init_db()


def _get_db():
    return SessionLocal()


# ── MCP Resources (discoverable data endpoints) ─────────────


@mcp.resource("resource://posts")
def resource_posts() -> str:
    """Recent LinkedIn posts (last 50)."""
    import json

    db = _get_db()
    try:
        return json.dumps(list_posts(db, limit=50), indent=2)
    finally:
        db.close()


@mcp.resource("resource://analytics")
def resource_analytics() -> str:
    """Full analytics snapshot across all posts."""
    import json

    db = _get_db()
    try:
        return json.dumps(
            get_analytics(db), default=str, indent=2,
        )
    finally:
        db.close()


@mcp.resource("resource://strategy")
def resource_strategy() -> str:
    """Current content strategy."""
    import json

    return json.dumps(get_strategy(), indent=2)


@mcp.resource("resource://top-posts")
def resource_top_posts() -> str:
    """Top 10 posts by engagement score."""
    import json

    db = _get_db()
    try:
        return json.dumps(get_top_posts(db, count=10), indent=2)
    finally:
        db.close()


# ── MCP Tools ────────────────────────────────────────────────


@mcp.tool()
def get_post_analytics() -> dict:
    """Get full analytics across all your LinkedIn posts.

    Returns aggregate metrics including engagement averages, distribution,
    top keywords, topic performance, timing analysis, readability metrics,
    and recommendations.

    Includes readability_vs_engagement (how reading level correlates with
    engagement), emoji_vs_engagement, and avg_readability across all posts.

    TIP: You can use the post texts and engagement data to classify
    hook types (question, story, data, contrarian, etc.) and narrative
    structures (list, story, problem-solution, etc.) yourself. Look at
    the opening lines of top_posts to identify what hooks work best.
    """
    db = _get_db()
    try:
        return get_analytics(db)
    finally:
        db.close()


@mcp.tool()
def get_posts(limit: int = 50, offset: int = 0) -> list:
    """Get your stored LinkedIn posts with readability metrics.

    Each post includes text, engagement stats, and readability metrics
    (Flesch-Kincaid grade, avg sentence length, vocabulary richness,
    emoji density, hashtag count, word count).

    TIP: Analyze the opening lines of high-engagement posts to identify
    hook patterns. Compare post structures (lists, stories, how-tos)
    to find what resonates with this creator's audience.

    Args:
        limit: Maximum number of posts to return (default 50).
        offset: Number of posts to skip for pagination.
    """
    db = _get_db()
    try:
        return list_posts(db, limit=limit, offset=offset)
    finally:
        db.close()


@mcp.tool()
def get_top_posts_tool(count: int = 5) -> list:
    """Get your best-performing LinkedIn posts ranked by engagement.

    Args:
        count: Number of top posts to return (default 5).
    """
    db = _get_db()
    try:
        return get_top_posts(db, count=count)
    finally:
        db.close()


@mcp.tool()
def get_posting_recommendations() -> dict:
    """Get data-driven recommendations for when, what, and how to post.

    Returns insights on best days, hours, topics, post length, language,
    readability level, and emoji usage based on your historical post
    performance.

    TIP: Combine these numeric recommendations with your own analysis
    of the user's top posts to suggest specific hook types, narrative
    structures, and content approaches.
    """
    db = _get_db()
    try:
        return get_recommendations(db)
    finally:
        db.close()


@mcp.tool()
def search_posts_tool(query: str, limit: int = 20) -> list:
    """Search your LinkedIn posts by keyword.

    Args:
        query: Search term to look for in post text.
        limit: Maximum number of results (default 20).
    """
    db = _get_db()
    try:
        return search_posts(db, query=query, limit=limit)
    finally:
        db.close()


@mcp.tool()
def get_post_count_tool() -> dict:
    """Get the total number of LinkedIn posts stored."""
    db = _get_db()
    try:
        return {"count": get_post_count(db)}
    finally:
        db.close()


@mcp.tool()
def get_strategy_tool() -> dict:
    """Get your current LinkedIn content strategy.

    Returns your defined strategy (topics, audience, goals, tone, etc.)
    or an empty template with descriptions of each field if no strategy
    has been set up yet. Use this to understand what to ask the user
    when helping them define their strategy.
    """
    return get_strategy()


@mcp.tool()
def update_strategy(
    topics: list[str] | None = None,
    audience: str | None = None,
    goals: str | None = None,
    frequency: str | None = None,
    tone: str | None = None,
    languages: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """Update the user's LinkedIn content strategy.

    Call this to save strategy choices after discussing them
    with the user.
    Only provide the fields you want to update — others
    will be preserved.

    Args:
        topics: List of topics the user writes about.
            E.g., ["AI/ML", "Data Engineering"].
        audience: Who they're writing for.
            E.g., "Senior engineers and tech leads".
        goals: What they want to achieve.
            E.g., "Thought leadership and hiring".
        frequency: How often they want to post.
            E.g., "3 times per week".
        tone: Preferred writing style.
            E.g., "Conversational and direct".
        languages: Languages they post in.
            E.g., ["English", "Italian"].
        notes: Any additional context for AI assistants.
    """
    return update_strategy_fields(
        topics=topics,
        audience=audience,
        goals=goals,
        frequency=frequency,
        tone=tone,
        languages=languages,
        notes=notes,
    )


@mcp.tool()
def analyze_draft(text: str) -> dict:
    """Analyze a draft LinkedIn post before publishing.

    Computes readability metrics for the draft and compares them
    against the creator's historical averages and top-performing
    posts. Returns the draft's metrics, historical averages,
    top posts averages, and a plain-English comparison.

    Use this to check if a draft's readability, length, and style
    match what has historically performed well for this creator.

    TIP: After getting the numeric comparison, you should also
    analyze the draft's hook (opening line) and structure yourself
    by comparing to the creator's top posts from get_top_posts.

    Args:
        text: The full text of the draft post to analyze.
    """
    db = _get_db()
    try:
        return svc_analyze_draft(db, text)
    finally:
        db.close()


@mcp.tool()
def get_engagement_velocity(
    post_id: int | None = None,
) -> dict | list:
    """Get engagement velocity for a post or recent posts.

    Shows how fast engagement is growing over time, based on
    re-scraping snapshots. Includes per-interval rates and a
    trajectory classification (accelerating, peaked, steady,
    declining).

    If post_id is provided, returns velocity for that specific
    post. Otherwise returns velocity for the 5 most recent posts
    that have snapshot data.

    Re-scraping happens automatically when you collect posts
    using the Chrome extension. Posts younger than 14 days get
    their engagement numbers updated on each scrape.

    Args:
        post_id: Specific post ID to check, or None for recent.
    """
    db = _get_db()
    try:
        if post_id is not None:
            return get_velocity(db, post_id)
        return get_recent_velocity(db)
    finally:
        db.close()


@mcp.tool()
def get_trends_tool(days: int = 90) -> dict:
    """Get engagement trends over time.

    Shows weekly engagement averages, post counts, and totals
    for the specified period. Use this to understand whether
    engagement is growing, declining, or flat over time.

    Args:
        days: Number of days to look back (default 90).
    """
    db = _get_db()
    try:
        return svc_get_trends(db, days=days)
    finally:
        db.close()


@mcp.tool()
def suggest_strategy_from_data() -> dict:
    """Analyze your LinkedIn post history and suggest a content strategy.

    Use this as the first step when helping a user set up their
    strategy. It examines their actual post performance to suggest
    topics, timing, length, and language based on what has worked
    best for them.

    After getting suggestions, walk the user through each section,
    presenting the data-driven insights and asking for their input
    before saving with update_strategy.
    """
    db = _get_db()
    try:
        return get_strategy_suggestions(db)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
