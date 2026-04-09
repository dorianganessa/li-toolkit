"""Tests for extended scraping fields (post type, hashtags, has_link)."""

from analytics import _analyze_post_types

# ---------------------------------------------------------------------------
# Saving and retrieving extended fields
# ---------------------------------------------------------------------------


class TestExtendedFieldsSave:
    def test_save_with_post_type(self, client):
        posts = [{
            "text": "Check out this image post!",
            "likes": 10,
            "comments": 2,
            "post_type": "image",
            "hashtags": ["#linkedin", "#content"],
            "has_link": False,
        }]
        resp = client.post("/api/posts", json=posts)
        assert resp.json()["saved"] == 1

    def test_save_without_extended_fields(self, client):
        """Old extension without extended fields should still work."""
        posts = [{"text": "Plain post", "likes": 5, "comments": 1}]
        resp = client.post("/api/posts", json=posts)
        assert resp.json()["saved"] == 1

    def test_list_includes_extended_fields(self, client):
        posts = [{
            "text": "Extended fields test",
            "likes": 10,
            "comments": 2,
            "post_type": "carousel",
            "hashtags": ["#test"],
            "has_link": True,
        }]
        client.post("/api/posts", json=posts)
        resp = client.get("/api/posts")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["post_type"] == "carousel"
        assert data[0]["hashtags"] == ["#test"]
        assert data[0]["has_link"] is True

    def test_list_extended_fields_null_graceful(self, client):
        """Posts without extended fields return clean defaults."""
        posts = [{"text": "No extended fields", "likes": 0, "comments": 0}]
        client.post("/api/posts", json=posts)
        resp = client.get("/api/posts")
        data = resp.json()
        assert data[0]["post_type"] is None
        assert data[0]["hashtags"] == []
        assert data[0]["has_link"] is None


# ---------------------------------------------------------------------------
# Post type analytics
# ---------------------------------------------------------------------------


class TestPostTypeAnalytics:
    def test_basic_grouping(self):
        posts = [
            {"post_type": "text", "engagement": 50, "impressions": 1000},
            {"post_type": "text", "engagement": 70, "impressions": 2000},
            {"post_type": "image", "engagement": 100, "impressions": 3000},
            {"post_type": "carousel", "engagement": 200, "impressions": 5000},
        ]
        result = _analyze_post_types(posts)
        by_type = {r["post_type"]: r for r in result}

        assert by_type["text"]["count"] == 2
        assert by_type["text"]["avg_engagement"] == 60.0
        assert by_type["image"]["count"] == 1
        assert by_type["carousel"]["count"] == 1

    def test_sorted_by_engagement(self):
        posts = [
            {"post_type": "text", "engagement": 10, "impressions": 100},
            {"post_type": "image", "engagement": 100, "impressions": 1000},
        ]
        result = _analyze_post_types(posts)
        assert result[0]["post_type"] == "image"

    def test_null_post_type_grouped_as_unknown(self):
        posts = [
            {"post_type": None, "engagement": 50, "impressions": 500},
            {"engagement": 30, "impressions": 300},
        ]
        result = _analyze_post_types(posts)
        unknown = [r for r in result if r["post_type"] == "unknown"]
        assert len(unknown) == 1
        assert unknown[0]["count"] == 2

    def test_analytics_includes_post_type_stats(self, client):
        posts = [
            {
                "text": "Text post here with enough words",
                "likes": 10,
                "comments": 2,
                "post_type": "text",
            },
            {
                "text": "Image post with some content too",
                "likes": 50,
                "comments": 8,
                "post_type": "image",
            },
        ]
        client.post("/api/posts", json=posts)
        data = client.get("/api/analytics").json()
        assert "post_type_stats" in data
        assert len(data["post_type_stats"]) >= 1
