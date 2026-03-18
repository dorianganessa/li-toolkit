"""Strategy storage and suggestion engine."""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from analytics import (
    _analyze_day_of_week,
    _analyze_hour,
    _analyze_keywords,
    _analyze_language,
    _analyze_length,
    _analyze_topics,
    _build_post_data,
    _has_temporal_data,
)
from database import PostRecord

# Default path — configurable via set_strategy_path()
_strategy_path = Path(__file__).parent / "strategy.json"

STRATEGY_TEMPLATE = {
    "topics": {
        "description": (
            "Topics you write about. List your core"
            " topics and optionally which ones you"
            " want to grow."
        ),
        "value": [],
    },
    "audience": {
        "description": "Who you're writing for. Job titles, seniority, industry, etc.",
        "value": "",
    },
    "goals": {
        "description": (
            "What you want to achieve with your"
            " LinkedIn content. E.g., thought"
            " leadership, hiring, lead generation."
        ),
        "value": "",
    },
    "frequency": {
        "description": "How often you want to post. E.g., '3 times per week', 'daily'.",
        "value": "",
    },
    "tone": {
        "description": (
            "Your preferred writing style. E.g.,"
            " 'conversational and direct',"
            " 'professional but approachable'."
        ),
        "value": "",
    },
    "languages": {
        "description": "Languages you post in.",
        "value": [],
    },
    "notes": {
        "description": "Anything else an AI should know when helping you draft posts.",
        "value": "",
    },
}


def set_strategy_path(path: Path) -> None:
    global _strategy_path
    _strategy_path = path


def load_strategy() -> dict:
    """Load strategy from disk, or return the empty template."""
    if _strategy_path.exists():
        return json.loads(_strategy_path.read_text())
    return STRATEGY_TEMPLATE


def save_strategy(strategy: dict) -> dict:
    """Save strategy to disk. Merges with template to ensure all fields exist."""
    merged = {**STRATEGY_TEMPLATE, **strategy}
    _strategy_path.write_text(json.dumps(merged, indent=2))
    return merged


def suggest_strategy(db: Session) -> dict:
    """Analyze post history and suggest a strategy based on what works."""
    records = db.query(PostRecord).all()

    if not records:
        return {
            "has_data": False,
            "message": (
                "No posts stored yet. Collect your LinkedIn"
                " posts first using the Chrome extension,"
                " then I can analyze your performance and"
                " suggest a strategy."
            ),
        }

    posts = _build_post_data(records)
    total = len(posts)

    # Gather insights
    topic_stats = _analyze_topics(posts)
    keyword_stats = _analyze_keywords(posts)
    language_stats = _analyze_language(posts)
    length_stats = _analyze_length(posts)
    has_dates = _has_temporal_data(posts)

    suggestions = {
        "has_data": True,
        "total_posts_analyzed": total,
        "topic_suggestions": [],
        "audience_hints": [],
        "frequency_suggestion": None,
        "tone_hints": [],
        "language_suggestion": [],
        "timing_suggestion": None,
        "length_suggestion": None,
    }

    # Topic suggestions — rank by engagement
    if topic_stats:
        suggestions["topic_suggestions"] = [
            {
                "topic": t["topic"],
                "post_count": t["count"],
                "avg_engagement": t["avg_engagement"],
                "recommendation": "strong performer" if t["avg_engagement"] > sum(
                    s["avg_engagement"] for s in topic_stats
                ) / len(topic_stats) else "below average",
            }
            for t in topic_stats
        ]

    # Top keywords as tone/content hints
    if keyword_stats:
        suggestions["tone_hints"] = [
            f"Posts mentioning '{k['keyword']}' average"
            f" {k['avg_engagement']} engagement"
            for k in keyword_stats[:5]
        ]

    # Language suggestion
    if language_stats:
        suggestions["language_suggestion"] = [
            {
                "language": lang["language"],
                "post_count": lang["count"],
                "avg_engagement": lang["avg_engagement"],
            }
            for lang in language_stats
        ]

    # Posting frequency from data
    posts_with_dates = [p for p in posts if p["published_at"] is not None]
    if len(posts_with_dates) >= 2:
        sorted_dates = sorted(p["published_at"] for p in posts_with_dates)
        span_days = (sorted_dates[-1] - sorted_dates[0]).days or 1
        posts_per_week = round(len(posts_with_dates) / span_days * 7, 1)
        suggestions["frequency_suggestion"] = {
            "current_rate": f"{posts_per_week} posts/week",
            "span_days": span_days,
            "total_dated_posts": len(posts_with_dates),
        }

    # Timing suggestion
    if has_dates:
        day_stats = _analyze_day_of_week(posts)
        hour_stats = _analyze_hour(posts)
        days_with_posts = [d for d in day_stats if d["count"] >= 1]
        hours_with_posts = [h for h in hour_stats if h["count"] >= 1]

        timing = {}
        if days_with_posts:
            best_day = max(days_with_posts, key=lambda d: d["avg_engagement"])
            timing["best_day"] = best_day["day"]
            timing["best_day_avg_engagement"] = best_day["avg_engagement"]
        if hours_with_posts:
            best_hour = max(hours_with_posts, key=lambda h: h["avg_engagement"])
            timing["best_hour"] = best_hour["hour"]
            timing["best_hour_avg_engagement"] = best_hour["avg_engagement"]
        if timing:
            suggestions["timing_suggestion"] = timing

    # Length suggestion
    if length_stats:
        best_length = max(length_stats, key=lambda x: x["avg_engagement"])
        suggestions["length_suggestion"] = {
            "best_length": best_length["label"],
            "range": best_length["range"],
            "avg_engagement": best_length["avg_engagement"],
            "post_count": best_length["count"],
        }

    return suggestions
