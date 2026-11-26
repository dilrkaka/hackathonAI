from fastapi import APIRouter, HTTPException, Query

from backend.app.search.loader import get_search_engine
from src.search.engine import family_of
from src.search.recommend import cross_sell

router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"]
)


@router.get("/{product_id}")
def get_recommendations(
    product_id: str,
    limit: int = Query(4, ge=1, le=10)
):
    search_engine = get_search_engine()

    anchor = next(
        (
            p for p in search_engine.offers
            if str(p["id"]) == product_id
        ),
        None
    )

    if anchor is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    used = {family_of(anchor)}

    recommendations = cross_sell(
        search_engine,
        anchor,
        used,
        limit
    )

    return {
        "product_id": product_id,
        "total": len(recommendations),
        "recommendations": recommendations
    }