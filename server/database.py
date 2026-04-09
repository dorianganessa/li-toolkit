"""SQLite database configuration and post table definition."""

import os
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
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
    last_scraped_at = Column(DateTime, nullable=True)
    edited = Column(Boolean, nullable=True, default=False)
    post_type = Column(String, nullable=True)
    hashtags = Column(Text, nullable=True)  # JSON array as string
    has_link = Column(Boolean, nullable=True)


class PostSnapshot(Base):
    """Engagement snapshot for tracking velocity over time."""

    __tablename__ = "post_snapshots"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    post_id: int = Column(
        Integer, ForeignKey("posts.id"), nullable=False,
    )
    likes: int = Column(Integer, default=0)
    comments: int = Column(Integer, default=0)
    reposts: int = Column(Integer, default=0)
    impressions: int = Column(Integer, default=0)
    scraped_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_snapshot_post_time", "post_id", "scraped_at"),
    )


def init_db() -> None:
    """Create all tables and apply lightweight migrations."""
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        cols = [
            row[1]
            for row in conn.execute(
                text("PRAGMA table_info(posts)"),
            ).fetchall()
        ]
        migrations = {
            "published_at": "ALTER TABLE posts ADD COLUMN published_at DATETIME",
            "last_scraped_at": "ALTER TABLE posts ADD COLUMN last_scraped_at DATETIME",
            "edited": "ALTER TABLE posts ADD COLUMN edited BOOLEAN DEFAULT 0",
            "post_type": "ALTER TABLE posts ADD COLUMN post_type VARCHAR",
            "hashtags": "ALTER TABLE posts ADD COLUMN hashtags TEXT",
            "has_link": "ALTER TABLE posts ADD COLUMN has_link BOOLEAN",
        }
        applied = False
        for col_name, ddl in migrations.items():
            if col_name not in cols:
                conn.execute(text(ddl))
                applied = True
        if applied:
            conn.commit()


def get_db() -> Session:
    """Yield a database session (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db  # type: ignore[misc]
    finally:
        db.close()
