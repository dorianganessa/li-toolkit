"""REST API routes."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import LinkedInPost, SaveResponse
from services import ServiceError
from services import analyze_draft as svc_analyze_draft
from services import get_analytics as svc_analytics
from services import get_post_count as svc_count
from services import get_recent_velocity as svc_recent_velocity
from services import get_recommendations as svc_recommendations
from services import get_strategy as svc_get_strategy
from services import get_strategy_suggestions as svc_suggestions
from services import get_top_posts as svc_top_posts
from services import get_trends as svc_trends
from services import get_velocity as svc_velocity
from services import list_posts as svc_list_posts
from services import save_posts as svc_save_posts
from services import search_posts as svc_search
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


@router.get("/posts/top")
def top_posts(
    count: int = Query(5, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return top posts ranked by engagement score."""
    return svc_top_posts(db, count=count)


@router.get("/posts/search")
def search_posts(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Search posts by keyword in text."""
    return svc_search(db, query=query, limit=limit)


@router.get("/posts/{post_id}/velocity")
def post_velocity(
    post_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get engagement velocity for a specific post."""
    return svc_velocity(db, post_id)


@router.get("/velocity/recent")
def recent_velocity(
    count: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get velocity for the most recent re-scraped posts."""
    return svc_recent_velocity(db, count=count)


@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)) -> dict:
    """Return full analytics computed across all stored posts."""
    return svc_analytics(db)


@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)) -> dict:
    """Return data-driven posting recommendations."""
    return svc_recommendations(db)


@router.post("/analyze-draft")
def analyze_draft(
    text: str = Body(..., embed=True),
    db: Session = Depends(get_db),
) -> dict:
    """Analyze a draft post's readability against historical data."""
    return svc_analyze_draft(db, text)


@router.get("/trends")
def get_trends(
    days: int = Query(90, ge=7, le=365),
    db: Session = Depends(get_db),
) -> dict:
    """Get engagement trends over time."""
    return svc_trends(db, days=days)


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
