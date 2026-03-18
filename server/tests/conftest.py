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
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


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
def sample_posts():
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
            "text": "Leadership lessons from scaling a data team at a startup",
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
