"""MCP server exposing LinkedIn analytics to LLM clients."""

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure local imports work when running standalone
sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal, init_db  # noqa: E402
from services import analyze_draft as svc_analyze_draft  # noqa: E402
from services import (  # noqa: E402
    get_analytics,
    get_post_count,
    get_recommendations,
    get_strategy,
    get_strategy_suggestions,
    get_top_posts,
    list_posts,
    search_posts,
    update_strategy_fields,
)

mcp = FastMCP(
    "li-toolkit",
    instructions="Access your LinkedIn post history and analytics",
)

# Initialize the database once at import time
init_db()


def _get_db():
    return SessionLocal()


@mcp.tool()
def get_post_analytics() -> str:
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
        metrics = get_analytics(db)
        return json.dumps(metrics, default=str, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_posts(limit: int = 50, offset: int = 0) -> str:
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
        posts = list_posts(db, limit=limit, offset=offset)
        return json.dumps(posts, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_top_posts_tool(count: int = 5) -> str:
    """Get your best-performing LinkedIn posts ranked by engagement.

    Args:
        count: Number of top posts to return (default 5).
    """
    db = _get_db()
    try:
        posts = get_top_posts(db, count=count)
        return json.dumps(posts, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_posting_recommendations() -> str:
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
        recs = get_recommendations(db)
        return json.dumps(recs, default=str, indent=2)
    finally:
        db.close()


@mcp.tool()
def search_posts_tool(query: str, limit: int = 20) -> str:
    """Search your LinkedIn posts by keyword.

    Args:
        query: Search term to look for in post text.
        limit: Maximum number of results (default 20).
    """
    db = _get_db()
    try:
        posts = search_posts(db, query=query, limit=limit)
        return json.dumps(posts, indent=2)
    finally:
        db.close()


@mcp.tool()
def get_post_count_tool() -> str:
    """Get the total number of LinkedIn posts stored."""
    db = _get_db()
    try:
        count = get_post_count(db)
        return json.dumps({"count": count})
    finally:
        db.close()


@mcp.tool()
def get_strategy_tool() -> str:
    """Get your current LinkedIn content strategy.

    Returns your defined strategy (topics, audience, goals, tone, etc.)
    or an empty template with descriptions of each field if no strategy
    has been set up yet. Use this to understand what to ask the user
    when helping them define their strategy.
    """
    strategy = get_strategy()
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
    saved = update_strategy_fields(
        topics=topics,
        audience=audience,
        goals=goals,
        frequency=frequency,
        tone=tone,
        languages=languages,
        notes=notes,
    )
    return json.dumps(saved, indent=2)


@mcp.tool()
def analyze_draft(text: str) -> str:
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
        result = svc_analyze_draft(db, text)
        return json.dumps(result, default=str, indent=2)
    finally:
        db.close()


@mcp.tool()
def suggest_strategy_from_data() -> str:
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
        suggestions = get_strategy_suggestions(db)
        return json.dumps(suggestions, default=str, indent=2)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
