"""Tests for the REST API endpoints."""


def test_save_posts(client, sample_posts):
    resp = client.post("/api/posts", json=sample_posts)
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == 3
    assert data["duplicates"] == 0
    assert data["total"] == 3


def test_save_posts_deduplication(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.post("/api/posts", json=sample_posts)
    data = resp.json()
    assert data["saved"] == 0
    assert data["duplicates"] == 3


def test_save_posts_partial_duplicate(client, sample_posts):
    client.post("/api/posts", json=sample_posts[:1])
    resp = client.post("/api/posts", json=sample_posts)
    data = resp.json()
    assert data["saved"] == 2
    assert data["duplicates"] == 1


def test_list_posts_empty(client):
    resp = client.get("/api/posts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_posts(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/posts")
    assert resp.status_code == 200
    posts = resp.json()
    assert len(posts) == 3
    assert all(key in posts[0] for key in ["id", "text", "likes", "comments"])


def test_list_posts_pagination(client, sample_posts):
    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/posts?limit=2&offset=0")
    assert len(resp.json()) == 2
    resp = client.get("/api/posts?limit=2&offset=2")
    assert len(resp.json()) == 1


def test_post_count(client, sample_posts):
    resp = client.get("/api/posts/count")
    assert resp.json()["count"] == 0

    client.post("/api/posts", json=sample_posts)
    resp = client.get("/api/posts/count")
    assert resp.json()["count"] == 3


def test_save_post_minimal_fields(client):
    posts = [{"text": "Hello world", "likes": 0, "comments": 0}]
    resp = client.post("/api/posts", json=posts)
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1


def test_save_empty_list(client):
    resp = client.post("/api/posts", json=[])
    assert resp.status_code == 200
    assert resp.json()["saved"] == 0
