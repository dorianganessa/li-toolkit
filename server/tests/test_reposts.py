"""Tests for repost flag storage and exclude_reposts filter."""

from database import PostRecord
from models import LinkedInPost
from repost_filter import exclude_reposts
from services import get_analytics, get_top_posts, save_posts


def test_exclude_reposts_filter():
    records = [
        PostRecord(text="mine", likes=1, comments=0, is_repost=False),
        PostRecord(text="theirs", likes=99, comments=0, is_repost=True),
    ]
    filtered = exclude_reposts(records)
    assert len(filtered) == 1
    assert filtered[0].text == "mine"


def test_save_repost_flag(db_session):
    save_posts(db_session, [
        LinkedInPost(
            text="Original post about leadership",
            likes=100,
            comments=10,
            reposts=5,
        ),
        LinkedInPost(
            text="Someone else's viral quote",
            likes=2000,
            comments=50,
            reposts=80000,
            is_repost=True,
            original_author="Bianca Arrighini",
        ),
    ])
    posts = db_session.query(PostRecord).all()
    assert sum(1 for p in posts if p.is_repost) == 1
    assert any(p.original_author == "Bianca Arrighini" for p in posts)


def test_analytics_exclude_reposts(db_session):
    save_posts(db_session, [
        LinkedInPost(text="My original post", likes=50, comments=5, reposts=2),
        LinkedInPost(
            text="Reposted content",
            likes=5000,
            comments=100,
            reposts=50000,
            is_repost=True,
            original_author="Other Author",
        ),
    ])

    metrics = get_analytics(db_session)
    assert metrics["empty"] is False
    assert metrics["total_posts"] == 1
    assert metrics["avg_likes"] == 50.0


def test_top_posts_exclude_reposts(db_session):
    save_posts(db_session, [
        LinkedInPost(text="Small original", likes=10, comments=1, reposts=0),
        LinkedInPost(
            text="Huge repost",
            likes=9000,
            comments=200,
            reposts=90000,
            is_repost=True,
            original_author="Other Author",
        ),
    ])

    top = get_top_posts(db_session, count=5)
    assert len(top) == 1
    assert "Small original" in top[0]["text"]


def test_repost_flag_updated_on_rescrape(client):
    client.post("/api/posts", json=[{
        "text": "Maybe a repost",
        "likes": 10,
        "comments": 1,
        "is_repost": False,
    }])
    client.post("/api/posts", json=[{
        "text": "Maybe a repost",
        "likes": 10,
        "comments": 1,
        "is_repost": True,
        "original_author": "Bianca Arrighini",
    }])

    posts = client.get("/api/posts").json()
    assert posts[0]["is_repost"] is True
    assert posts[0]["original_author"] == "Bianca Arrighini"
