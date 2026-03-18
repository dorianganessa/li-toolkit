"""REST API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import LinkedInPost, SaveResponse
from services import ServiceError
from services import get_analytics as svc_analytics
from services import get_post_count as svc_count
from services import get_strategy as svc_get_strategy
from services import get_strategy_suggestions as svc_suggestions
from services import list_posts as svc_list_posts
from services import save_posts as svc_save_posts
from strategy import save_strategy

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/posts", response_model=SaveResponse)
def save_posts(
    posts: list[LinkedInPost],
    db: Session = Depends(get_db),
) -> SaveResponse:
    """Receive posts from the extension, skipping duplicates."""
    try:
        result = svc_save_posts(db, posts)
    except ServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.message,
        ) from exc
    return SaveResponse(**result)


@router.get("/posts")
def list_posts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return saved posts, most recent first."""
    return svc_list_posts(db, limit=limit, offset=offset)


@router.get("/posts/count")
def post_count(db: Session = Depends(get_db)) -> dict:
    """Return total number of stored posts."""
    return {"count": svc_count(db)}


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)) -> dict:
    """Return full analytics computed across all stored posts."""
    return svc_analytics(db)


@router.get("/strategy")
def get_strategy() -> dict:
    """Return the current content strategy, or an empty template."""
    return svc_get_strategy()


@router.put("/strategy")
def update_strategy(strategy: dict) -> dict:
    """Save or update the content strategy."""
    return save_strategy(strategy)


@router.get("/strategy/suggest")
def get_strategy_suggestions(
    db: Session = Depends(get_db),
) -> dict:
    """Analyze post history and suggest a data-driven strategy."""
    return svc_suggestions(db)
