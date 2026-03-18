"""REST API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from analytics import compute_metrics
from database import PostRecord, get_db
from models import LinkedInPost, SaveResponse
from strategy import load_strategy, save_strategy, suggest_strategy

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/posts", response_model=SaveResponse)
def save_posts(
    posts: list[LinkedInPost],
    db: Session = Depends(get_db),
) -> SaveResponse:
    """Receive a list of posts from the extension and save them, skipping duplicates."""
    saved = 0
    duplicates = 0

    for post in posts:
        exists = (
            db.query(PostRecord).filter(PostRecord.text_hash == post.text_hash).first()
        )
        if exists:
            duplicates += 1
            continue

        record = PostRecord(
            text_hash=post.text_hash,
            text=post.text,
            likes=post.likes,
            comments=post.comments,
            reposts=post.reposts,
            impressions=post.impressions,
            published_at=post.published_at,
        )
        db.add(record)
        saved += 1

    db.commit()
    return SaveResponse(saved=saved, duplicates=duplicates, total=len(posts))


@router.get("/posts")
def list_posts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return saved posts, most recent first."""
    records = (
        db.query(PostRecord)
        .order_by(PostRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "text": r.text,
            "likes": r.likes,
            "comments": r.comments,
            "reposts": r.reposts,
            "impressions": r.impressions,
            "published_at": str(r.published_at) if r.published_at else None,
            "created_at": str(r.created_at),
        }
        for r in records
    ]


@router.get("/posts/count")
def post_count(db: Session = Depends(get_db)) -> dict:
    """Return total number of stored posts."""
    count = db.query(PostRecord).count()
    return {"count": count}


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)) -> dict:
    """Return full analytics computed across all stored posts."""
    return compute_metrics(db)


@router.get("/strategy")
def get_strategy() -> dict:
    """Return the current content strategy, or an empty template."""
    return load_strategy()


@router.put("/strategy")
def update_strategy(strategy: dict) -> dict:
    """Save or update the content strategy."""
    return save_strategy(strategy)


@router.get("/strategy/suggest")
def get_strategy_suggestions(db: Session = Depends(get_db)) -> dict:
    """Analyze post history and suggest a data-driven strategy."""
    return suggest_strategy(db)
