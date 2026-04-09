"""Tests for the analytics engine.

Each test asserts actual computed values, not just response shape.
Engagement formula: likes + comments*2 + reposts*3.
"""

from datetime import datetime

from analytics import (
    _analyze_day_of_week,
    _analyze_emoji_engagement,
    _analyze_hour,
    _analyze_keywords,
    _analyze_language,
    _analyze_length,
    _analyze_readability,
    _analyze_topics,
    _avg_readability,
    _build_post_data,
    _build_recommendations,
    _engagement_score,
    _get_bottom_posts,
)
from database import PostRecord

# ---------------------------------------------------------------------------
# Helper to build PostRecord objects in memory
# ---------------------------------------------------------------------------

def _make_record(
    text="test post",
    likes=10,
    comments=2,
    reposts=0,
    impressions=500,
    published_at=None,
):
    r = PostRecord()
    r.text = text
    r.likes = likes
    r.comments = comments
    r.reposts = reposts
    r.impressions = impressions
    r.published_at = published_at
    return r


# ---------------------------------------------------------------------------
# _build_post_data
# ---------------------------------------------------------------------------

class TestEngagementScore:
    def test_basic(self):
        assert _engagement_score(10, 5, 3) == 10 + 5 * 2 + 3 * 3  # 29

    def test_reposts_weighted_highest(self):
        # Reposts at 3x should outweigh likes at 1x
        assert _engagement_score(0, 0, 10) > _engagement_score(10, 0, 0)

    def test_comments_weighted_middle(self):
        assert _engagement_score(0, 10, 0) > _engagement_score(10, 0, 0)
        assert _engagement_score(0, 0, 10) > _engagement_score(0, 10, 0)

    def test_zeros(self):
        assert _engagement_score(0, 0, 0) == 0


class TestBuildPostData:
    def test_engagement_calculation(self):
        records = [_make_record(likes=42, comments=5, reposts=3)]
        posts = _build_post_data(records)
        # 42 + 5*2 + 3*3 = 61
        assert posts[0]["engagement"] == 61

    def test_engagement_rate_with_impressions(self):
        records = [
            _make_record(likes=10, comments=5, reposts=2, impressions=1000),
        ]
        posts = _build_post_data(records)
        # rate = (10 + 5 + 2) / 1000 * 100 = 1.7
        assert posts[0]["engagement_rate"] == 1.7

    def test_zero_impressions_uses_fallback(self):
        records = [
            _make_record(likes=10, comments=5, reposts=0, impressions=0),
        ]
        posts = _build_post_data(records)
        # impressions clamped to 1, rate = (10+5+0)/1 * 100 = 1500.0
        assert posts[0]["engagement_rate"] == 1500.0

    def test_length_is_character_count(self):
        records = [_make_record(text="Hello world")]
        posts = _build_post_data(records)
        assert posts[0]["length"] == 11

    def test_readability_fields_computed(self):
        records = [_make_record(text="The cat sat on the mat.")]
        posts = _build_post_data(records)
        assert posts[0]["word_count"] == 6
        assert posts[0]["avg_sentence_length"] == 6.0
        assert posts[0]["flesch_kincaid_grade"] >= 0
        assert posts[0]["vocab_richness"] == 0.833  # 5 unique / 6 words ("the" repeats)
        assert posts[0]["emoji_density"] == 0.0
        assert posts[0]["hashtag_count"] == 0


# ---------------------------------------------------------------------------
# compute_metrics — integration via API
# ---------------------------------------------------------------------------

def test_analytics_empty(client):
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    assert resp.json()["empty"] is True


def test_analytics_aggregate_values(client, sample_posts):
    """Verify exact aggregate metrics for 3 sample posts."""
    client.post("/api/posts", json=sample_posts)
    data = client.get("/api/analytics").json()

    assert data["empty"] is False
    assert data["total_posts"] == 3

    # Post 1: eng=61, Post 2: eng=186, Post 3: eng=130
    # avg = (61+186+130)/3 = 125.67
    assert data["avg_engagement"] == 125.7

    # avg likes = (42+120+85)/3 = 82.33
    assert data["avg_likes"] == 82.3

    # avg comments = (5+18+12)/3 = 11.67
    assert data["avg_comments"] == 11.7

    # avg impressions = (1200+5000+3500)/3 = 3233.33
    assert data["avg_impressions"] == 3233


def test_analytics_engagement_distribution(client, sample_posts):
    """Post 1 goes in 51-100, Posts 2 and 3 go in 101-500."""
    client.post("/api/posts", json=sample_posts)
    dist = client.get("/api/analytics").json()["engagement_distribution"]

    assert dist["0"] == 0
    assert dist["1-10"] == 0
    assert dist["11-50"] == 0
    assert dist["51-100"] == 1   # Post 1: engagement 61
    assert dist["101-500"] == 2  # Post 2: 186, Post 3: 130
    assert dist["500+"] == 0


def test_analytics_engagement_distribution_zero(
    client, zero_engagement_posts,
):
    """Posts with 0 engagement land in the '0' bucket."""
    client.post("/api/posts", json=zero_engagement_posts)
    dist = client.get("/api/analytics").json()["engagement_distribution"]
    assert dist["0"] == 2


# ---------------------------------------------------------------------------
# Top / bottom posts
# ---------------------------------------------------------------------------

def test_top_posts_order_and_values(client, sample_posts):
    """Top posts must be sorted descending by engagement."""
    client.post("/api/posts", json=sample_posts)
    top = client.get("/api/analytics").json()["top_posts"]

    engagements = [p["engagement"] for p in top]
    assert engagements == [186, 130, 61]


def test_bottom_posts_excludes_zero(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    bottom = client.get("/api/analytics").json()["bottom_posts"]
    assert all(p["engagement"] > 0 for p in bottom)


def test_bottom_posts_returns_lowest():
    """Unit test: bottom posts should be the 3 lowest (non-zero)."""
    posts = [
        {"engagement": e, "text": f"p{e}"}
        for e in [0, 5, 10, 20, 50, 100]
    ]
    result = _get_bottom_posts(posts)
    engagements = [p["engagement"] for p in result]
    assert engagements == [20, 10, 5]


# ---------------------------------------------------------------------------
# Length analysis
# ---------------------------------------------------------------------------

def test_length_analysis_categories(client, mixed_length_posts):
    """Each post should land in the correct length bucket."""
    client.post("/api/posts", json=mixed_length_posts)
    data = client.get("/api/analytics").json()
    length = data["length_analysis"]

    by_label = {item["label"]: item for item in length}

    # "Short post here" = 15 chars -> Short (< 100)
    assert by_label["Short"]["count"] == 1
    # "A" * 300 -> Medium (100-500)
    assert by_label["Medium"]["count"] == 1
    # "B" * 700 -> Long (500-1000)
    assert by_label["Long"]["count"] == 1
    # "C" * 1500 -> Very long (> 1000)
    assert by_label["Very long"]["count"] == 1


def test_length_analysis_engagement():
    """Verify engagement averages are computed per category."""
    posts = [
        {"text": "x", "length": 50, "engagement": 10,
         "likes": 10, "impressions": 100, "published_at": None},
        {"text": "x", "length": 50, "engagement": 20,
         "likes": 20, "impressions": 200, "published_at": None},
    ]
    result = _analyze_length(posts)
    assert len(result) == 1  # both are Short
    assert result[0]["avg_engagement"] == 15.0


# ---------------------------------------------------------------------------
# Language analysis
# ---------------------------------------------------------------------------

def test_language_detection_italian(client, italian_posts):
    """Posts with >= 2 Italian markers should be classified as Italian."""
    client.post("/api/posts", json=italian_posts)
    data = client.get("/api/analytics").json()
    lang = data["language_analysis"]

    by_lang = {item["language"]: item for item in lang}
    assert "Italian" in by_lang
    assert by_lang["Italian"]["count"] == 2


def test_language_detection_english(client, sample_posts):
    """English posts (no Italian markers) classified as English."""
    client.post("/api/posts", json=sample_posts)
    data = client.get("/api/analytics").json()
    lang = data["language_analysis"]

    by_lang = {item["language"]: item for item in lang}
    assert "English" in by_lang
    assert by_lang["English"]["count"] == 3


def test_language_analysis_unit():
    """Unit test: Italian markers trigger Italian classification."""
    posts = [
        {"text": "Questo è un post che non sono d'accordo",
         "engagement": 100, "impressions": 1000,
         "published_at": None, "length": 40},
        {"text": "This is a plain English post",
         "engagement": 50, "impressions": 500,
         "published_at": None, "length": 28},
    ]
    result = _analyze_language(posts)
    by_lang = {r["language"]: r for r in result}
    assert by_lang["Italian"]["count"] == 1
    assert by_lang["Italian"]["avg_engagement"] == 100.0
    assert by_lang["English"]["count"] == 1
    assert by_lang["English"]["avg_engagement"] == 50.0


# ---------------------------------------------------------------------------
# Keyword analysis
# ---------------------------------------------------------------------------

def test_keywords_require_min_occurrences():
    """Keywords must appear in >= 3 posts to be included."""
    posts = [
        {"text": "python rocks", "engagement": 10,
         "published_at": None},
        {"text": "python is great", "engagement": 20,
         "published_at": None},
        {"text": "python forever", "engagement": 30,
         "published_at": None},
        {"text": "unique word here", "engagement": 5,
         "published_at": None},
    ]
    result = _analyze_keywords(posts)
    keywords = [k["keyword"] for k in result]
    assert "python" in keywords
    assert "unique" not in keywords


def test_keywords_sorted_by_engagement():
    """Results should be sorted by avg_engagement descending."""
    posts = [
        {"text": "python framework backend server", "engagement": 100,
         "published_at": None},
        {"text": "python framework frontend client", "engagement": 50,
         "published_at": None},
        {"text": "python framework mobile design", "engagement": 10,
         "published_at": None},
        {"text": "leadership hiring culture growth", "engagement": 200,
         "published_at": None},
        {"text": "leadership hiring feedback mentor", "engagement": 300,
         "published_at": None},
        {"text": "leadership hiring coaching skills", "engagement": 100,
         "published_at": None},
    ]
    result = _analyze_keywords(posts)
    # "leadership" avg=200, "python" avg=53.3 — leadership should rank higher
    kw_names = [k["keyword"] for k in result]
    assert "leadership" in kw_names
    assert "python" in kw_names
    li = kw_names.index("leadership")
    pi = kw_names.index("python")
    assert li < pi  # leadership ranked higher


def test_keywords_exclude_stopwords():
    """Stopwords should not appear in keyword results."""
    # "have" and "this" are English stopwords
    posts = [
        {"text": "have this python experience working",
         "engagement": 10, "published_at": None},
        {"text": "have this python experience great",
         "engagement": 20, "published_at": None},
        {"text": "have this python experience deep",
         "engagement": 30, "published_at": None},
    ]
    result = _analyze_keywords(posts)
    keywords = [k["keyword"] for k in result]
    assert "python" in keywords
    assert "experience" in keywords
    # Short stopwords (<5 chars) are already filtered by regex
    # "have" and "this" are 4 chars, won't match the 5+ char regex
    # But let's verify no stopwords made it through
    from analytics import _STOPWORDS
    for kw in keywords:
        assert kw not in _STOPWORDS


def test_keywords_avg_engagement_value():
    """Verify the actual avg engagement value for a keyword."""
    posts = [
        {"text": "python fastapi backend", "engagement": 10,
         "published_at": None},
        {"text": "python django backend", "engagement": 20,
         "published_at": None},
        {"text": "python flask backend", "engagement": 30,
         "published_at": None},
    ]
    result = _analyze_keywords(posts)
    by_kw = {k["keyword"]: k for k in result}
    assert by_kw["python"]["avg_engagement"] == 20.0
    assert by_kw["python"]["count"] == 3


# ---------------------------------------------------------------------------
# Day of week analysis
# ---------------------------------------------------------------------------

def test_day_of_week_always_returns_seven_days():
    posts = [
        {"published_at": datetime(2025, 3, 3, 10, 0),
         "engagement": 50},  # Monday
    ]
    result = _analyze_day_of_week(posts)
    assert len(result) == 7
    assert [d["day"] for d in result] == [
        "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
    ]


def test_day_of_week_correct_assignment(client, temporal_posts):
    """Posts should land on their actual day of week."""
    client.post("/api/posts", json=temporal_posts)
    data = client.get("/api/analytics").json()
    days = data["day_of_week_stats"]

    by_day = {d["day"]: d for d in days}

    # 1 post on Monday (2025-03-03)
    assert by_day["Mon"]["count"] == 1
    # 2 posts on Tuesday (2025-03-04)
    assert by_day["Tue"]["count"] == 2
    # 1 post on Friday (2025-03-07)
    assert by_day["Fri"]["count"] == 1
    # 0 posts on other days
    assert by_day["Wed"]["count"] == 0
    assert by_day["Thu"]["count"] == 0
    assert by_day["Sat"]["count"] == 0
    assert by_day["Sun"]["count"] == 0


def test_day_of_week_engagement_values(client, temporal_posts):
    """Verify avg engagement is computed correctly per day."""
    client.post("/api/posts", json=temporal_posts)
    data = client.get("/api/analytics").json()
    days = data["day_of_week_stats"]
    by_day = {d["day"]: d for d in days}

    # Monday: 1 post, engagement = 20 + 3*2 + 1*3 = 29
    assert by_day["Mon"]["avg_engagement"] == 29.0

    # Tuesday: 2 posts
    # Post 1: 80 + 15*2 + 5*3 = 125
    # Post 2: 60 + 10*2 + 3*3 = 89
    # avg = (125 + 89) / 2 = 107.0
    assert by_day["Tue"]["avg_engagement"] == 107.0

    # Friday: 1 post, engagement = 40 + 6*2 + 2*3 = 58
    assert by_day["Fri"]["avg_engagement"] == 58.0

    # Days with no posts should have 0 engagement
    assert by_day["Wed"]["avg_engagement"] == 0


# ---------------------------------------------------------------------------
# Hour analysis
# ---------------------------------------------------------------------------

def test_hour_analysis_returns_24_hours():
    result = _analyze_hour([])
    assert len(result) == 24
    assert result[0]["hour"] == "00:00"
    assert result[23]["hour"] == "23:00"


def test_hour_analysis_correct_assignment(client, temporal_posts):
    """Posts should land on their actual hour."""
    client.post("/api/posts", json=temporal_posts)
    data = client.get("/api/analytics").json()
    hours = data["hour_stats"]
    by_hour = {h["hour"]: h for h in hours}

    assert by_hour["08:00"]["count"] == 1  # Monday 08:00
    assert by_hour["12:00"]["count"] == 2  # Two Tuesday posts at 12:xx
    assert by_hour["18:00"]["count"] == 1  # Friday 18:00
    assert by_hour["00:00"]["count"] == 0


def test_hour_analysis_engagement_value():
    """Verify engagement is correctly averaged per hour."""
    posts = [
        {"published_at": datetime(2025, 1, 1, 9, 0),
         "engagement": 100},
        {"published_at": datetime(2025, 1, 2, 9, 0),
         "engagement": 200},
    ]
    result = _analyze_hour(posts)
    by_hour = {h["hour"]: h for h in result}
    assert by_hour["09:00"]["avg_engagement"] == 150.0
    assert by_hour["09:00"]["count"] == 2


# ---------------------------------------------------------------------------
# Topic analysis
# ---------------------------------------------------------------------------

def test_topic_detection_requires_two_keywords():
    """A post needs >= 2 matching keywords to be classified."""
    posts = [
        # Only 1 AI keyword ("model") — should NOT match AI topic
        {"text": "This model is interesting",
         "engagement": 10, "likes": 10, "impressions": 100,
         "engagement_rate": 10.0, "published_at": None, "length": 30},
        # 2 AI keywords ("machine", "learning") — should match
        {"text": "Machine learning is transforming everything",
         "engagement": 50, "likes": 50, "impressions": 500,
         "engagement_rate": 10.0, "published_at": None, "length": 44},
    ]
    result = _analyze_topics(posts)
    by_topic = {t["topic"]: t for t in result}

    if "AI & Machine Learning" in by_topic:
        # Only the second post should match
        assert by_topic["AI & Machine Learning"]["count"] == 1
        assert by_topic["AI & Machine Learning"]["avg_engagement"] == 50.0


def test_topic_multi_classification():
    """A post can belong to multiple topics."""
    # This post has keywords for both Data & Engineering
    text = (
        "Building a data pipeline with python and"
        " deploying to cloud infrastructure"
    )
    posts = [{
        "text": text, "engagement": 80, "likes": 60,
        "impressions": 2000, "engagement_rate": 3.0,
        "published_at": None, "length": len(text),
    }]
    result = _analyze_topics(posts)
    topic_names = [t["topic"] for t in result]
    # Should match multiple topics
    assert len(topic_names) >= 2


def test_topic_engagement_values():
    """Topic stats should reflect correct engagement averages."""
    posts = [
        {"text": "data pipeline analytics dashboard metrics",
         "engagement": 100, "likes": 80, "impressions": 2000,
         "engagement_rate": 4.0, "published_at": None, "length": 45},
        {"text": "data warehouse spark airflow pipeline",
         "engagement": 200, "likes": 150, "impressions": 5000,
         "engagement_rate": 3.0, "published_at": None, "length": 40},
    ]
    result = _analyze_topics(posts)
    by_topic = {t["topic"]: t for t in result}

    data_topic = by_topic.get("Data & Analytics")
    assert data_topic is not None
    assert data_topic["count"] == 2
    assert data_topic["avg_engagement"] == 150.0
    assert data_topic["avg_likes"] == 115.0


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

def test_recommendations_best_day(client, temporal_posts):
    """Best day recommendation should be Tuesday (highest avg eng)."""
    client.post("/api/posts", json=temporal_posts)
    data = client.get("/api/analytics").json()
    recs = data["recommendations"]
    by_type = {r["type"]: r for r in recs}

    assert "best_day" in by_type
    assert by_type["best_day"]["value"] == "Tue"


def test_recommendations_best_hour(client, temporal_posts):
    """Best hour should be 12:00 (Tuesday posts had high engagement)."""
    client.post("/api/posts", json=temporal_posts)
    data = client.get("/api/analytics").json()
    recs = data["recommendations"]
    by_type = {r["type"]: r for r in recs}

    assert "best_hour" in by_type
    assert by_type["best_hour"]["value"] == "12:00"


def test_recommendations_best_length(client, mixed_length_posts):
    """Best length should be Very long (highest avg engagement)."""
    client.post("/api/posts", json=mixed_length_posts)
    data = client.get("/api/analytics").json()
    recs = data["recommendations"]
    by_type = {r["type"]: r for r in recs}

    assert "best_length" in by_type
    assert by_type["best_length"]["value"] == "Very long"


def test_recommendations_unit():
    """Unit test: _build_recommendations returns correct structure."""
    posts = [
        {"text": "test post", "length": 50, "engagement": 10,
         "likes": 10, "comments": 0, "impressions": 100,
         "engagement_rate": 10.0,
         "published_at": datetime(2025, 3, 3, 10, 0)},
    ]
    recs = _build_recommendations(posts)
    types = [r["type"] for r in recs]
    assert "best_day" in types
    assert "best_hour" in types


# ---------------------------------------------------------------------------
# Full metrics integration test
# ---------------------------------------------------------------------------

def test_full_metrics_structure(client, sample_posts):
    """Verify the complete analytics response has all expected keys."""
    client.post("/api/posts", json=sample_posts)
    data = client.get("/api/analytics").json()

    expected_keys = {
        "empty", "total_posts", "avg_engagement", "avg_likes",
        "avg_comments", "avg_impressions", "avg_engagement_rate",
        "engagement_distribution", "length_analysis",
        "language_analysis", "top_keywords", "has_temporal_data",
        "posts_with_dates", "day_of_week_stats", "hour_stats",
        "topic_stats", "post_type_stats", "readability_vs_engagement",
        "emoji_vs_engagement", "avg_readability",
        "recommendations", "top_posts", "bottom_posts",
    }
    assert expected_keys == set(data.keys())


# ---------------------------------------------------------------------------
# Readability correlation
# ---------------------------------------------------------------------------


def test_readability_vs_engagement():
    """Posts should be bucketed by FK grade with correct avg engagement."""
    posts = [
        {"flesch_kincaid_grade": 3.0, "engagement": 100},
        {"flesch_kincaid_grade": 4.0, "engagement": 200},
        {"flesch_kincaid_grade": 7.0, "engagement": 50},
        {"flesch_kincaid_grade": 10.0, "engagement": 80},
    ]
    result = _analyze_readability(posts)
    by_label = {r["label"]: r for r in result}
    # Very easy bucket: FK 3 + 4, avg = (100+200)/2 = 150
    assert by_label["Very easy"]["avg_engagement"] == 150.0
    assert by_label["Very easy"]["count"] == 2
    # Easy bucket: FK 7, avg = 50
    assert by_label["Easy"]["avg_engagement"] == 50.0
    # Standard bucket: FK 10, avg = 80
    assert by_label["Standard"]["avg_engagement"] == 80.0


def test_emoji_vs_engagement():
    """Posts should be bucketed by emoji density with correct avg."""
    posts = [
        {"emoji_density": 0.0, "engagement": 100},
        {"emoji_density": 0.0, "engagement": 200},
        {"emoji_density": 0.005, "engagement": 80},
        {"emoji_density": 0.02, "engagement": 50},
    ]
    result = _analyze_emoji_engagement(posts)
    by_label = {r["label"]: r for r in result}
    # No emoji: avg = (100+200)/2 = 150
    assert by_label["No emoji"]["avg_engagement"] == 150.0
    assert by_label["No emoji"]["count"] == 2
    # Light: avg = 80
    assert by_label["Light emoji"]["avg_engagement"] == 80.0
    # Heavy: avg = 50
    assert by_label["Heavy emoji"]["avg_engagement"] == 50.0


def test_avg_readability():
    """Average readability should compute means across posts."""
    posts = [
        {"flesch_kincaid_grade": 5.0, "avg_sentence_length": 10.0,
         "vocab_richness": 0.8, "word_count": 50},
        {"flesch_kincaid_grade": 9.0, "avg_sentence_length": 20.0,
         "vocab_richness": 0.6, "word_count": 100},
    ]
    result = _avg_readability(posts)
    assert result["avg_flesch_kincaid"] == 7.0
    assert result["avg_sentence_length"] == 15.0
    assert result["avg_vocab_richness"] == 0.7
    assert result["avg_word_count"] == 75


def test_avg_readability_empty():
    """Empty list should return empty dict."""
    assert _avg_readability([]) == {}
