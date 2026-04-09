"""Tests for re-scraping, snapshots, and engagement velocity."""

from datetime import datetime, timedelta

from analytics import (
    compute_velocity,
    detect_trajectory,
    get_engagement_trend,
)
from database import PostRecord, PostSnapshot

# ---------------------------------------------------------------------------
# Re-scraping: save_posts updates recent duplicates
# ---------------------------------------------------------------------------


class TestRescraping:
    def test_new_post_saved_normally(self, client):
        posts = [{"text": "Brand new post", "likes": 10, "comments": 2}]
        resp = client.post("/api/posts", json=posts)
        data = resp.json()
        assert data["saved"] == 1
        assert data["updated"] == 0
        assert data["duplicates"] == 0

    def test_old_duplicate_skipped(self, client, db_session):
        """Posts older than 14 days should not be re-scraped."""
        # Insert a post dated 20 days ago
        old = PostRecord(
            text_hash="0c94d7735ba54936d7d4d138c7da3318ad94ee8fbc402ff23312d5b19da8bda3",
            text="Old post",
            likes=5,
            comments=1,
            reposts=0,
            impressions=100,
            created_at=datetime.utcnow() - timedelta(days=20),
            last_scraped_at=datetime.utcnow() - timedelta(days=20),
        )
        db_session.add(old)
        db_session.commit()

        posts = [{"text": "Old post", "likes": 50, "comments": 10}]
        resp = client.post("/api/posts", json=posts)
        data = resp.json()
        assert data["duplicates"] == 1
        assert data["updated"] == 0

    def test_recent_duplicate_updated(self, client, db_session):
        """Posts younger than 14 days get engagement updated."""
        recent = PostRecord(
            text_hash=(
                "f6e0a1e2ac41945a9aa7ff8a8aaa0ceb"
                "c12a3bcc981a929ad5cf810a090e11ae"
            ),
            text="111",
            likes=5,
            comments=1,
            reposts=0,
            impressions=100,
            created_at=datetime.utcnow() - timedelta(days=2),
            last_scraped_at=datetime.utcnow() - timedelta(hours=12),
        )
        db_session.add(recent)
        db_session.commit()

        posts = [{
            "text": "111",
            "likes": 50,
            "comments": 10,
            "reposts": 5,
            "impressions": 500,
        }]
        resp = client.post("/api/posts", json=posts)
        data = resp.json()
        assert data["updated"] == 1
        assert data["duplicates"] == 0

        # Check engagement was updated
        db_session.expire_all()
        updated = (
            db_session.query(PostRecord)
            .filter(PostRecord.text == "111")
            .first()
        )
        assert updated.likes == 50
        assert updated.comments == 10

    def test_rescrape_creates_snapshot(self, client, db_session):
        """Re-scraping should create a snapshot of the previous state."""
        recent = PostRecord(
            text_hash=(
                "f6e0a1e2ac41945a9aa7ff8a8aaa0ceb"
                "c12a3bcc981a929ad5cf810a090e11ae"
            ),
            text="111",
            likes=5,
            comments=1,
            reposts=0,
            impressions=100,
            created_at=datetime.utcnow() - timedelta(days=1),
            last_scraped_at=datetime.utcnow() - timedelta(hours=8),
        )
        db_session.add(recent)
        db_session.commit()
        post_id = recent.id

        posts = [{
            "text": "111",
            "likes": 50,
            "comments": 10,
            "reposts": 5,
            "impressions": 500,
        }]
        client.post("/api/posts", json=posts)

        snapshots = (
            db_session.query(PostSnapshot)
            .filter(PostSnapshot.post_id == post_id)
            .all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].likes == 5  # Previous state
        assert snapshots[0].comments == 1

    def test_too_recent_scrape_skipped(self, client, db_session):
        """Posts scraped less than 6h ago should not be re-scraped."""
        recent = PostRecord(
            text_hash=(
                "f6e0a1e2ac41945a9aa7ff8a8aaa0ceb"
                "c12a3bcc981a929ad5cf810a090e11ae"
            ),
            text="111",
            likes=5,
            comments=1,
            reposts=0,
            impressions=100,
            created_at=datetime.utcnow() - timedelta(days=1),
            last_scraped_at=datetime.utcnow() - timedelta(hours=2),
        )
        db_session.add(recent)
        db_session.commit()

        posts = [{
            "text": "111",
            "likes": 50,
            "comments": 10,
        }]
        resp = client.post("/api/posts", json=posts)
        data = resp.json()
        assert data["duplicates"] == 1
        assert data["updated"] == 0

    def test_max_snapshots_respected(self, client, db_session):
        """Should not create more than 10 snapshots per post."""
        recent = PostRecord(
            text_hash=(
                "f6e0a1e2ac41945a9aa7ff8a8aaa0ceb"
                "c12a3bcc981a929ad5cf810a090e11ae"
            ),
            text="111",
            likes=5,
            comments=1,
            reposts=0,
            impressions=100,
            created_at=datetime.utcnow() - timedelta(days=1),
            last_scraped_at=datetime.utcnow() - timedelta(hours=8),
        )
        db_session.add(recent)
        db_session.commit()

        # Pre-fill 10 snapshots
        for i in range(10):
            db_session.add(PostSnapshot(
                post_id=recent.id,
                likes=i,
                comments=0,
                reposts=0,
                impressions=0,
                scraped_at=datetime.utcnow() - timedelta(hours=100 - i),
            ))
        db_session.commit()

        posts = [{
            "text": "111",
            "likes": 50,
            "comments": 10,
        }]
        client.post("/api/posts", json=posts)

        count = (
            db_session.query(PostSnapshot)
            .filter(PostSnapshot.post_id == recent.id)
            .count()
        )
        assert count == 10  # No new snapshot added

    def test_save_response_includes_updated(self, client, sample_posts):
        """SaveResponse should always include the updated field."""
        resp = client.post("/api/posts", json=sample_posts)
        data = resp.json()
        assert "updated" in data


# ---------------------------------------------------------------------------
# Velocity analysis
# ---------------------------------------------------------------------------


class TestVelocity:
    def test_no_snapshots_returns_none(self, db_session):
        post = PostRecord(
            text_hash="vel1",
            text="Test",
            likes=10,
            comments=2,
            reposts=0,
            impressions=100,
        )
        db_session.add(post)
        db_session.commit()

        result = compute_velocity(db_session, post.id)
        assert result is None

    def test_velocity_with_snapshots(self, db_session):
        now = datetime.utcnow()
        post = PostRecord(
            text_hash="vel2",
            text="Velocity test",
            likes=100,
            comments=20,
            reposts=10,
            impressions=5000,
            created_at=now - timedelta(hours=24),
            last_scraped_at=now,
        )
        db_session.add(post)
        db_session.commit()

        db_session.add(PostSnapshot(
            post_id=post.id,
            likes=10,
            comments=2,
            reposts=1,
            impressions=500,
            scraped_at=now - timedelta(hours=24),
        ))
        db_session.add(PostSnapshot(
            post_id=post.id,
            likes=50,
            comments=10,
            reposts=5,
            impressions=2000,
            scraped_at=now - timedelta(hours=12),
        ))
        db_session.commit()

        result = compute_velocity(db_session, post.id)
        assert result is not None
        assert result["snapshots"] == 2
        assert len(result["intervals"]) == 2
        assert result["total_engagement_gained"] > 0
        assert "trajectory" in result

    def test_velocity_engagement_delta(self, db_session):
        """Engagement delta should use the new formula."""
        now = datetime.utcnow()
        post = PostRecord(
            text_hash="vel3",
            text="Delta test",
            likes=30,
            comments=10,
            reposts=5,
            impressions=1000,
            created_at=now - timedelta(hours=6),
            last_scraped_at=now,
        )
        db_session.add(post)
        db_session.commit()

        db_session.add(PostSnapshot(
            post_id=post.id,
            likes=10,
            comments=2,
            reposts=1,
            impressions=200,
            scraped_at=now - timedelta(hours=6),
        ))
        db_session.commit()

        result = compute_velocity(db_session, post.id)
        # Snapshot: 10 + 2*2 + 1*3 = 17
        # Current: 30 + 10*2 + 5*3 = 65
        # Delta = 48
        assert result["total_engagement_gained"] == 48


# ---------------------------------------------------------------------------
# Trajectory detection
# ---------------------------------------------------------------------------


class TestTrajectory:
    def test_insufficient_data(self):
        assert detect_trajectory([]) == "insufficient_data"
        assert detect_trajectory(
            [{"engagement_per_hour": 5}],
        ) == "insufficient_data"

    def test_accelerating(self):
        intervals = [
            {"engagement_per_hour": 10},
            {"engagement_per_hour": 20},
        ]
        assert detect_trajectory(intervals) == "accelerating"

    def test_declining(self):
        intervals = [
            {"engagement_per_hour": 20},
            {"engagement_per_hour": 5},
        ]
        assert detect_trajectory(intervals) == "declining"

    def test_steady(self):
        intervals = [
            {"engagement_per_hour": 10},
            {"engagement_per_hour": 11},
        ]
        assert detect_trajectory(intervals) == "steady"

    def test_peaked(self):
        intervals = [
            {"engagement_per_hour": 5},
            {"engagement_per_hour": 15},
            {"engagement_per_hour": 25},
            {"engagement_per_hour": 8},
        ]
        assert detect_trajectory(intervals) == "peaked"


# ---------------------------------------------------------------------------
# Engagement trends
# ---------------------------------------------------------------------------


class TestTrends:
    def test_empty_db(self, db_session):
        result = get_engagement_trend(db_session, days=90)
        assert result == []

    def test_weekly_grouping(self, db_session):
        now = datetime.utcnow()
        for i in range(3):
            db_session.add(PostRecord(
                text_hash=f"trend{i}",
                text=f"Trend post {i}",
                likes=10 * (i + 1),
                comments=2,
                reposts=1,
                impressions=500,
                created_at=now - timedelta(days=i),
            ))
        db_session.commit()

        result = get_engagement_trend(db_session, days=90)
        assert len(result) >= 1
        assert all("week" in w for w in result)
        assert all("avg_engagement" in w for w in result)
        assert all("posts" in w for w in result)
