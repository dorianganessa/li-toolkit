"""Tests for Pydantic models."""

from models import LinkedInPost, SaveResponse


def test_linkedin_post_hash():
    post = LinkedInPost(text="Hello world", likes=10, comments=2)
    assert len(post.text_hash) == 64  # SHA-256


def test_linkedin_post_same_hash():
    p1 = LinkedInPost(text="Same text", likes=10, comments=2)
    p2 = LinkedInPost(text="Same text", likes=50, comments=20)
    assert p1.text_hash == p2.text_hash


def test_linkedin_post_different_hash():
    p1 = LinkedInPost(text="Text A", likes=10, comments=2)
    p2 = LinkedInPost(text="Text B", likes=10, comments=2)
    assert p1.text_hash != p2.text_hash


def test_linkedin_post_defaults():
    post = LinkedInPost(text="Hello", likes=1, comments=0)
    assert post.reposts == 0
    assert post.impressions == 0
    assert post.published_at is None


def test_save_response():
    resp = SaveResponse(saved=5, duplicates=2, total=7)
    assert resp.saved == 5
    assert resp.duplicates == 2
    assert resp.total == 7
