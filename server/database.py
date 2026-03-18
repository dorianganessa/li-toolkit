"""SQLite database configuration and post table definition."""

import os
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Database path — configurable via LI_TOOLKIT_DB env var
_db_path = os.environ.get(
    "LI_TOOLKIT_DB",
    str(Path(__file__).parent / "linkedin_data.db"),
)
DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class PostRecord(Base):
    """Table storing saved LinkedIn posts."""

    __tablename__ = "posts"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    text_hash: str = Column(String(64), unique=True, nullable=False, index=True)
    text: str = Column(Text, nullable=False)
    likes: int = Column(Integer, nullable=False, default=0)
    comments: int = Column(Integer, nullable=False, default=0)
    reposts: int = Column(Integer, nullable=False, default=0)
    impressions: int = Column(Integer, nullable=False, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def init_db() -> None:
    """Create all tables and apply lightweight migrations."""
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        cols = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(posts)")).fetchall()
        ]
        if "published_at" not in cols:
            conn.execute(text("ALTER TABLE posts ADD COLUMN published_at DATETIME"))
            conn.commit()


def get_db() -> Session:
    """Yield a database session (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()
