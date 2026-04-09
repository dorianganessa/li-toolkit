"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

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


def test_save_response_updated_default():
    """Updated field should default to 0 for backward compat."""
    resp = SaveResponse(saved=5, duplicates=2, total=7)
    assert resp.updated == 0


def test_save_response_with_updated():
    resp = SaveResponse(saved=3, duplicates=1, updated=2, total=6)
    assert resp.updated == 2


# ---- Validation ----

def test_reject_negative_likes():
    with pytest.raises(ValidationError):
        LinkedInPost(text="test", likes=-1, comments=0)


def test_reject_negative_comments():
    with pytest.raises(ValidationError):
        LinkedInPost(text="test", likes=0, comments=-1)


def test_reject_negative_reposts():
    with pytest.raises(ValidationError):
        LinkedInPost(text="test", likes=0, comments=0, reposts=-1)


def test_reject_negative_impressions():
    with pytest.raises(ValidationError):
        LinkedInPost(text="test", likes=0, comments=0, impressions=-1)


def test_extended_fields_optional():
    """Extended fields should be optional for backward compat."""
    post = LinkedInPost(text="test", likes=0, comments=0)
    assert post.post_type is None
    assert post.hashtags is None
    assert post.has_link is None


def test_extended_fields_accepted():
    post = LinkedInPost(
        text="test", likes=0, comments=0,
        post_type="image", hashtags=["#ai"], has_link=True,
    )
    assert post.post_type == "image"
    assert post.hashtags == ["#ai"]
    assert post.has_link is True
