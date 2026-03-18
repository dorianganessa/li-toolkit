"""Shared test fixtures."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set a temp DB before importing app modules
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["LI_TOOLKIT_DB"] = _tmp.name
_tmp.close()

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

_engine = create_engine(
    f"sqlite:///{_tmp.name}",
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(
    bind=_engine, autoflush=False, autocommit=False,
)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    """Recreate all tables before each test."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Provide a raw DB session for unit-testing services directly."""
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Post fixtures — each targets a specific testing scenario
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_posts():
    """Three posts with known engagement values for deterministic testing.

    Post 1: engagement = 42 + 5*2 = 52, bucket "51-100"
             Wed Jan 15 09:00, English, length 54 (Short)
    Post 2: engagement = 120 + 18*2 = 156, bucket "101-500"
             Mon Jan 20 14:30, English, length 60 (Short)
    Post 3: engagement = 85 + 12*2 = 109, bucket "101-500"
             Sat Feb 1 08:00, English, length 52 (Short)
    """
    return [
        {
            "text": "Just shipped a new feature using Python and FastAPI!",
            "likes": 42,
            "comments": 5,
            "reposts": 3,
            "impressions": 1200,
            "published_at": "2025-01-15T09:00:00",
        },
        {
            "text": (
                "Leadership lessons from scaling a data team"
                " at a startup"
            ),
            "likes": 120,
            "comments": 18,
            "reposts": 10,
            "impressions": 5000,
            "published_at": "2025-01-20T14:30:00",
        },
        {
            "text": "Machine learning models need good data pipelines",
            "likes": 85,
            "comments": 12,
            "reposts": 7,
            "impressions": 3500,
            "published_at": "2025-02-01T08:00:00",
        },
    ]


@pytest.fixture()
def zero_engagement_posts():
    """Posts with zero likes/comments to test edge cases."""
    return [
        {
            "text": "A quiet post that nobody engaged with at all",
            "likes": 0,
            "comments": 0,
            "reposts": 0,
            "impressions": 100,
            "published_at": "2025-03-01T10:00:00",
        },
        {
            "text": "Another silent post lost in the feed",
            "likes": 0,
            "comments": 0,
            "reposts": 0,
            "impressions": 50,
            "published_at": "2025-03-02T11:00:00",
        },
    ]


@pytest.fixture()
def italian_posts():
    """Italian-language posts (contain >= 2 Italian marker words)."""
    return [
        {
            "text": (
                "Questo è un post che parla di come sono cambiate"
                " le pipeline di dati nella mia azienda"
            ),
            "likes": 200,
            "comments": 30,
            "reposts": 15,
            "impressions": 8000,
            "published_at": "2025-01-10T12:00:00",
        },
        {
            "text": (
                "Non sono sicuro che questa tecnologia sia la"
                " scelta giusta per il nostro team"
            ),
            "likes": 150,
            "comments": 25,
            "reposts": 8,
            "impressions": 6000,
            "published_at": "2025-01-12T08:00:00",
        },
    ]


@pytest.fixture()
def mixed_length_posts():
    """Posts with different lengths to test length analysis."""
    return [
        {
            "text": "Short post here",
            "likes": 10,
            "comments": 2,
            "reposts": 0,
            "impressions": 200,
            "published_at": "2025-02-10T09:00:00",
        },
        {
            "text": "A" * 300,
            "likes": 30,
            "comments": 5,
            "reposts": 2,
            "impressions": 800,
            "published_at": "2025-02-11T10:00:00",
        },
        {
            "text": "B" * 700,
            "likes": 50,
            "comments": 8,
            "reposts": 4,
            "impressions": 1500,
            "published_at": "2025-02-12T11:00:00",
        },
        {
            "text": "C" * 1500,
            "likes": 100,
            "comments": 20,
            "reposts": 10,
            "impressions": 4000,
            "published_at": "2025-02-13T12:00:00",
        },
    ]


@pytest.fixture()
def temporal_posts():
    """Posts on known days/hours for testing temporal analysis.

    Mon 08:00, Tue 12:00, Tue 12:00, Fri 18:00
    """
    return [
        {
            "text": "Monday morning data engineering thoughts on pipelines",
            "likes": 20,
            "comments": 3,
            "reposts": 1,
            "impressions": 500,
            "published_at": "2025-03-03T08:00:00",  # Monday
        },
        {
            "text": (
                "Tuesday lunch post about software architecture"
                " and system design patterns"
            ),
            "likes": 80,
            "comments": 15,
            "reposts": 5,
            "impressions": 3000,
            "published_at": "2025-03-04T12:00:00",  # Tuesday
        },
        {
            "text": (
                "Another Tuesday lunch post about cloud infrastructure"
                " and kubernetes deployment"
            ),
            "likes": 60,
            "comments": 10,
            "reposts": 3,
            "impressions": 2000,
            "published_at": "2025-03-04T12:30:00",  # Tuesday
        },
        {
            "text": "Friday evening reflections on startup life and business",
            "likes": 40,
            "comments": 6,
            "reposts": 2,
            "impressions": 1000,
            "published_at": "2025-03-07T18:00:00",  # Friday
        },
    ]
