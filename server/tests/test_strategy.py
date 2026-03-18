"""Tests for the strategy system."""

import tempfile
from pathlib import Path

import strategy as strategy_module


def _use_temp_strategy():
    """Point strategy storage at a temp file."""
    tmp = Path(tempfile.mktemp(suffix=".json"))
    strategy_module.set_strategy_path(tmp)
    return tmp


def test_load_strategy_empty():
    _use_temp_strategy()
    s = strategy_module.load_strategy()
    assert "topics" in s
    assert "audience" in s
    assert "goals" in s
    assert s["topics"]["value"] == []
    assert s["audience"]["value"] == ""
    assert s["goals"]["value"] == ""


def test_save_and_load_strategy():
    _use_temp_strategy()
    data = strategy_module.load_strategy()
    data["topics"]["value"] = ["AI/ML", "Data Engineering"]
    data["audience"]["value"] = "Senior engineers"
    strategy_module.save_strategy(data)

    loaded = strategy_module.load_strategy()
    assert loaded["topics"]["value"] == ["AI/ML", "Data Engineering"]
    assert loaded["audience"]["value"] == "Senior engineers"


def test_save_preserves_template_fields():
    _use_temp_strategy()
    strategy_module.save_strategy({"topics": {"value": ["AI"]}})
    loaded = strategy_module.load_strategy()
    # Template fields should be preserved even if not provided
    assert "audience" in loaded
    assert "goals" in loaded
    assert "tone" in loaded
    assert "frequency" in loaded
    assert "languages" in loaded
    assert "notes" in loaded


def test_save_overwrites_values():
    """Saving twice should overwrite, not append."""
    _use_temp_strategy()
    data = strategy_module.load_strategy()
    data["topics"]["value"] = ["AI"]
    strategy_module.save_strategy(data)

    data["topics"]["value"] = ["Data"]
    strategy_module.save_strategy(data)

    loaded = strategy_module.load_strategy()
    assert loaded["topics"]["value"] == ["Data"]


def test_strategy_file_created_on_save():
    """Verify the file is actually written to disk."""
    path = _use_temp_strategy()
    assert not path.exists()

    strategy_module.save_strategy(strategy_module.load_strategy())
    assert path.exists()


def test_strategy_api_get(client):
    _use_temp_strategy()
    resp = client.get("/api/strategy")
    assert resp.status_code == 200
    data = resp.json()
    assert "topics" in data
    assert "value" in data["topics"]


def test_strategy_api_put(client):
    _use_temp_strategy()
    strategy = strategy_module.load_strategy()
    strategy["topics"]["value"] = ["Leadership"]
    strategy["tone"]["value"] = "Direct and conversational"

    resp = client.put("/api/strategy", json=strategy)
    assert resp.status_code == 200

    resp = client.get("/api/strategy")
    data = resp.json()
    assert data["topics"]["value"] == ["Leadership"]
    assert data["tone"]["value"] == "Direct and conversational"


def test_strategy_api_put_preserves_unset_fields(client):
    """PUT with partial data should keep template defaults."""
    _use_temp_strategy()
    resp = client.put(
        "/api/strategy",
        json={"topics": {"value": ["AI"]}},
    )
    assert resp.status_code == 200

    data = client.get("/api/strategy").json()
    assert data["topics"]["value"] == ["AI"]
    assert "audience" in data
    assert "goals" in data


def test_suggest_strategy_empty(client):
    resp = client.get("/api/strategy/suggest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_data"] is False
    assert "message" in data


def test_suggest_strategy_with_data(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/strategy/suggest")
    data = resp.json()

    assert data["has_data"] is True
    assert data["total_posts_analyzed"] == 3
    assert isinstance(data["topic_suggestions"], list)
    assert data["frequency_suggestion"] is not None
    assert data["timing_suggestion"] is not None


def test_suggest_strategy_topic_suggestions(client, sample_posts):
    """Topic suggestions should include avg_engagement and counts."""
    client.post("/api/posts", json=sample_posts)
    data = client.get("/api/strategy/suggest").json()

    for topic in data["topic_suggestions"]:
        assert "topic" in topic
        assert "post_count" in topic
        assert "avg_engagement" in topic
        assert topic["post_count"] > 0
        assert topic["avg_engagement"] > 0
        assert topic["recommendation"] in (
            "strong performer", "below average",
        )


def test_suggest_strategy_frequency(client, sample_posts):
    """Frequency suggestion should reflect the actual post rate."""
    client.post("/api/posts", json=sample_posts)
    data = client.get("/api/strategy/suggest").json()

    freq = data["frequency_suggestion"]
    assert freq["total_dated_posts"] == 3
    assert freq["span_days"] > 0
    assert "posts/week" in freq["current_rate"]
