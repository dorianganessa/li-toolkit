"""Tests for the analytics engine."""


def test_analytics_empty(client):
    resp = client.get("/api/analytics")
    assert resp.status_code == 200
    assert resp.json()["empty"] is True


def test_analytics_with_data(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    data = resp.json()

    assert data["empty"] is False
    assert data["total_posts"] == 3
    assert data["avg_likes"] > 0
    assert data["avg_comments"] > 0
    assert data["avg_impressions"] > 0
    assert data["avg_engagement"] > 0
    assert data["avg_engagement_rate"] > 0


def test_analytics_engagement_distribution(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    dist = resp.json()["engagement_distribution"]
    assert isinstance(dist, dict)
    assert sum(dist.values()) == 3


def test_analytics_topic_detection(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    topics = resp.json()["topic_stats"]
    assert isinstance(topics, list)
    topic_names = [t["topic"] for t in topics]
    # sample_posts mention ML, data, leadership, startup, python/fastapi
    assert any("Engineering" in t or "Data" in t or "AI" in t for t in topic_names)


def test_analytics_top_posts(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    top = resp.json()["top_posts"]
    assert len(top) <= 5
    # Should be sorted by engagement descending
    engagements = [p["engagement"] for p in top]
    assert engagements == sorted(engagements, reverse=True)


def test_analytics_recommendations(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    recs = resp.json()["recommendations"]
    assert isinstance(recs, list)


def test_analytics_length_analysis(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    length = resp.json()["length_analysis"]
    assert isinstance(length, list)
    assert all("label" in item and "count" in item for item in length)


def test_analytics_day_of_week(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    days = resp.json()["day_of_week_stats"]
    assert len(days) == 7
    assert days[0]["day"] == "Mon"
    assert days[6]["day"] == "Sun"


def test_analytics_hour_stats(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/analytics")
    hours = resp.json()["hour_stats"]
    assert len(hours) == 24
    assert hours[0]["hour"] == "00:00"
