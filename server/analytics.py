"""Analytics engine for LinkedIn post data."""

import re

from sqlalchemy.orm import Session

from database import PostRecord

# Common stopwords (English + Italian) to filter out of keyword analysis
_STOPWORDS = {
    # English
    "the", "and", "that", "this", "with", "for", "are", "but", "not", "you",
    "all", "can", "had", "her", "was", "one", "our", "out", "have", "has",
    "been", "from", "they", "will", "what", "when", "your", "which", "their",
    "about", "would", "there", "into", "more", "than", "them", "then", "just",
    "also", "know", "other", "some", "could", "time", "very", "most", "only",
    "like", "how", "need", "work", "don", "it's", "don't",
    # Italian
    "che", "per", "non", "con", "una", "del", "della", "delle", "dei", "degli",
    "nel", "nella", "nelle", "nei", "negli", "sul", "sulla", "sulle", "sui",
    "sugli", "dal", "dalla", "dalle", "dai", "dagli", "sono", "come", "anche",
    "questo", "questa", "questi", "queste", "quello", "quella", "quelli",
    "quelle", "alla", "alle", "agli", "essere", "avere", "fare", "dire",
    "cosa", "tutto", "tutti", "ogni", "solo", "dopo", "prima", "quando",
    "dove", "perche", "pero", "ancora", "senza", "molto", "piu", "meno",
    "deve", "modo", "fatto", "parte", "stato", "stati", "stata", "hanno",
    "loro", "nostro", "vostro", "proprio", "sempre", "gia",
}

# Italian marker words for language detection
_IT_MARKERS = {"che", "non", "per", "una", "sono", "anche", "questo", "della"}

# Topic clusters based on co-occurring keywords
TOPICS = {
    "AI & Machine Learning": {
        "artificial", "intelligence", "machine", "learning", "model", "models",
        "neural", "deep", "training", "prompt", "llm", "gpt", "claude",
        "openai", "chatgpt", "generative", "agents", "agent",
    },
    "Data & Analytics": {
        "data", "analytics", "database", "pipeline", "dashboard", "metrics",
        "warehouse", "lakehouse", "spark", "airflow", "etl", "bigquery",
        "snowflake", "databricks", "sql",
    },
    "Leadership & Management": {
        "leader", "leadership", "manager", "management", "team", "culture",
        "hiring", "feedback", "mentor", "coaching", "delegation",
    },
    "Career & Growth": {
        "career", "growth", "journey", "learn", "mistake", "lessons",
        "skills", "junior", "senior", "interview",
    },
    "Startup & Business": {
        "startup", "business", "founder", "product", "customer", "revenue",
        "market", "scale", "fundraising", "strategy",
    },
    "Engineering & Tech": {
        "software", "engineering", "code", "system", "architecture", "cloud",
        "deploy", "infrastructure", "kubernetes", "docker", "api",
        "microservices", "backend", "frontend", "python", "typescript",
    },
    "Personal & Storytelling": {
        "story", "personal", "experience", "life", "remember", "feeling",
        "emotion", "passion", "motivation",
    },
}


def _build_post_data(records: list[PostRecord]) -> list[dict]:
    """Transform database records into enriched post dicts."""
    posts = []
    for r in records:
        engagement = r.likes + r.comments * 2
        imp = r.impressions if r.impressions > 0 else 1
        engagement_rate = round((r.likes + r.comments) / imp * 100, 2)
        posts.append({
            "text": r.text,
            "likes": r.likes,
            "comments": r.comments,
            "reposts": r.reposts,
            "impressions": r.impressions,
            "engagement": engagement,
            "engagement_rate": engagement_rate,
            "length": len(r.text),
            "published_at": r.published_at,
        })
    return posts


def compute_metrics(db: Session) -> dict:
    """Compute all aggregate metrics across stored posts."""
    records = db.query(PostRecord).all()

    if not records:
        return {"empty": True}

    posts = _build_post_data(records)
    total = len(posts)

    avg_engagement = round(sum(p["engagement"] for p in posts) / total, 1)
    avg_likes = round(sum(p["likes"] for p in posts) / total, 1)
    avg_comments = round(sum(p["comments"] for p in posts) / total, 1)
    avg_impressions = round(sum(p["impressions"] for p in posts) / total, 0)
    avg_engagement_rate = round(sum(p["engagement_rate"] for p in posts) / total, 2)

    # Engagement distribution buckets
    buckets = {"0": 0, "1-10": 0, "11-50": 0, "51-100": 0, "101-500": 0, "500+": 0}
    for p in posts:
        e = p["engagement"]
        if e == 0:
            buckets["0"] += 1
        elif e <= 10:
            buckets["1-10"] += 1
        elif e <= 50:
            buckets["11-50"] += 1
        elif e <= 100:
            buckets["51-100"] += 1
        elif e <= 500:
            buckets["101-500"] += 1
        else:
            buckets["500+"] += 1

    return {
        "empty": False,
        "total_posts": total,
        "avg_engagement": avg_engagement,
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "avg_impressions": int(avg_impressions),
        "avg_engagement_rate": avg_engagement_rate,
        "engagement_distribution": buckets,
        "length_analysis": _analyze_length(posts),
        "language_analysis": _analyze_language(posts),
        "top_keywords": _analyze_keywords(posts),
        "has_temporal_data": _has_temporal_data(posts),
        "posts_with_dates": len([p for p in posts if p["published_at"]]),
        "day_of_week_stats": _analyze_day_of_week(posts),
        "hour_stats": _analyze_hour(posts),
        "topic_stats": _analyze_topics(posts),
        "recommendations": _build_recommendations(posts),
        "top_posts": sorted(posts, key=lambda p: p["engagement"], reverse=True)[:5],
        "bottom_posts": _get_bottom_posts(posts),
    }


def _has_temporal_data(posts: list[dict]) -> bool:
    return len([p for p in posts if p["published_at"] is not None]) >= 3


def _analyze_length(posts: list[dict]) -> list[dict]:
    """Analyze post length vs engagement."""
    categories = {
        "< 100": {"posts": [], "label": "Short"},
        "100-500": {"posts": [], "label": "Medium"},
        "500-1000": {"posts": [], "label": "Long"},
        "> 1000": {"posts": [], "label": "Very long"},
    }
    for p in posts:
        ln = p["length"]
        if ln < 100:
            categories["< 100"]["posts"].append(p)
        elif ln < 500:
            categories["100-500"]["posts"].append(p)
        elif ln < 1000:
            categories["500-1000"]["posts"].append(p)
        else:
            categories["> 1000"]["posts"].append(p)

    result = []
    for key, val in categories.items():
        ps = val["posts"]
        if ps:
            result.append({
                "label": val["label"],
                "range": key,
                "count": len(ps),
                "avg_engagement": round(sum(p["engagement"] for p in ps) / len(ps), 1),
                "avg_likes": round(sum(p["likes"] for p in ps) / len(ps), 1),
                "avg_impressions": round(sum(p["impressions"] for p in ps) / len(ps), 0),
            })
    return result


def _analyze_language(posts: list[dict]) -> list[dict]:
    """Detect post language (Italian vs English) and compare performance."""
    it_posts = []
    en_posts = []
    for p in posts:
        words = set(p["text"].lower().split())
        if len(words & _IT_MARKERS) >= 2:
            it_posts.append(p)
        else:
            en_posts.append(p)

    result = []
    for name, group in [("Italian", it_posts), ("English", en_posts)]:
        if group:
            result.append({
                "language": name,
                "count": len(group),
                "avg_engagement": round(
                    sum(p["engagement"] for p in group) / len(group), 1
                ),
                "avg_impressions": round(
                    sum(p["impressions"] for p in group) / len(group), 0
                ),
            })
    return result


def _analyze_keywords(posts: list[dict]) -> list[dict]:
    """Find top keywords by average engagement (min 3 occurrences)."""
    keyword_eng: dict[str, list[int]] = {}
    for p in posts:
        words = set(re.findall(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ]{5,}", p["text"].lower()))
        unique = words - _STOPWORDS
        for word in unique:
            keyword_eng.setdefault(word, []).append(p["engagement"])

    stats = []
    for word, engagements in keyword_eng.items():
        if len(engagements) >= 3:
            stats.append({
                "keyword": word,
                "count": len(engagements),
                "avg_engagement": round(sum(engagements) / len(engagements), 1),
                "total_engagement": sum(engagements),
            })

    stats.sort(key=lambda k: k["avg_engagement"], reverse=True)
    return stats[:12]


def _analyze_day_of_week(posts: list[dict]) -> list[dict]:
    """Analyze engagement by day of week."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_posts: dict[int, list[dict]] = {i: [] for i in range(7)}

    for p in posts:
        if p["published_at"] is not None:
            day_posts[p["published_at"].weekday()].append(p)

    result = []
    for i, name in enumerate(days):
        ps = day_posts[i]
        result.append({
            "day": name,
            "count": len(ps),
            "avg_engagement": round(
                sum(p["engagement"] for p in ps) / len(ps), 1
            ) if ps else 0,
        })
    return result


def _analyze_hour(posts: list[dict]) -> list[dict]:
    """Analyze engagement by hour of day."""
    hour_posts: dict[int, list[dict]] = {h: [] for h in range(24)}

    for p in posts:
        if p["published_at"] is not None:
            hour_posts[p["published_at"].hour].append(p)

    result = []
    for h in range(24):
        ps = hour_posts[h]
        result.append({
            "hour": f"{h:02d}:00",
            "count": len(ps),
            "avg_engagement": round(
                sum(p["engagement"] for p in ps) / len(ps), 1
            ) if ps else 0,
        })
    return result


def _analyze_topics(posts: list[dict]) -> list[dict]:
    """Classify posts into topic clusters and compare performance."""
    topic_posts: dict[str, list[dict]] = {t: [] for t in TOPICS}

    for p in posts:
        words = set(re.findall(r"[a-zA-ZàèéìòùÀÈÉÌÒÙ]{3,}", p["text"].lower()))
        for topic_name, topic_words in TOPICS.items():
            if len(words & topic_words) >= 2:
                topic_posts[topic_name].append(p)

    result = []
    for topic_name, tp in topic_posts.items():
        if tp:
            result.append({
                "topic": topic_name,
                "count": len(tp),
                "avg_engagement": round(
                    sum(p["engagement"] for p in tp) / len(tp), 1
                ),
                "avg_likes": round(sum(p["likes"] for p in tp) / len(tp), 1),
                "avg_impressions": round(
                    sum(p["impressions"] for p in tp) / len(tp), 0
                ),
                "avg_engagement_rate": round(
                    sum(p["engagement_rate"] for p in tp) / len(tp), 2
                ),
            })
    result.sort(key=lambda t: t["avg_engagement"], reverse=True)
    return result


def _build_recommendations(posts: list[dict]) -> list[dict]:
    """Generate actionable recommendations based on the data."""
    recs = []

    day_stats = _analyze_day_of_week(posts)
    days_with_posts = [d for d in day_stats if d["count"] >= 1]
    if days_with_posts:
        best_day = max(days_with_posts, key=lambda d: d["avg_engagement"])
        recs.append({
            "type": "best_day",
            "label": "Best day to post",
            "value": best_day["day"],
            "detail": f"Avg engagement {best_day['avg_engagement']} "
                      f"({best_day['count']} posts)",
        })

    hour_stats = _analyze_hour(posts)
    hours_with_posts = [h for h in hour_stats if h["count"] >= 1]
    if hours_with_posts:
        best_hour = max(hours_with_posts, key=lambda h: h["avg_engagement"])
        recs.append({
            "type": "best_hour",
            "label": "Best hour to post",
            "value": best_hour["hour"],
            "detail": f"Avg engagement {best_hour['avg_engagement']} "
                      f"({best_hour['count']} posts)",
        })

    topic_stats = _analyze_topics(posts)
    if topic_stats:
        best_topic = topic_stats[0]
        recs.append({
            "type": "best_topic",
            "label": "Best performing topic",
            "value": best_topic["topic"],
            "detail": f"Avg engagement {best_topic['avg_engagement']} "
                      f"({best_topic['count']} posts)",
        })

    length_analysis = _analyze_length(posts)
    if length_analysis:
        best_len = max(length_analysis, key=lambda x: x["avg_engagement"])
        recs.append({
            "type": "best_length",
            "label": "Ideal post length",
            "value": best_len["label"],
            "detail": f"Avg engagement {best_len['avg_engagement']} "
                      f"({best_len['count']} posts)",
        })

    lang_analysis = _analyze_language(posts)
    if len(lang_analysis) == 2:
        best_lang = max(lang_analysis, key=lambda x: x["avg_engagement"])
        recs.append({
            "type": "best_language",
            "label": "Best performing language",
            "value": best_lang["language"],
            "detail": f"Avg engagement {best_lang['avg_engagement']} "
                      f"({best_lang['count']} posts)",
        })

    return recs


def _get_bottom_posts(posts: list[dict]) -> list[dict]:
    """Get the 3 lowest-engagement posts (excluding zero-engagement)."""
    ranked = sorted(posts, key=lambda p: p["engagement"], reverse=True)
    with_engagement = [p for p in ranked if p["engagement"] > 0]
    return with_engagement[-3:] if len(with_engagement) >= 3 else with_engagement
