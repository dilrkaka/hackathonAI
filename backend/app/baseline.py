from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, case

from backend.app.database import engine
from backend.app.models import products, categories

router = APIRouter(
    prefix="/api/search",
    tags=["Search"]
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=12, ge=4, le=100)


@router.post("/baseline")
def baseline_search(request: SearchRequest):
    started = perf_counter()
    query = request.query.strip()

    pattern = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    pattern = f"%{pattern}%"

    condition = or_(
        products.c.name.ilike(pattern, escape="\\"),
        products.c.description.ilike(pattern, escape="\\")
    )

    score = case(
        (products.c.name.ilike(pattern, escape="\\"), 2),
        else_=1
    )

    stmt = select(
        products,
        categories.c.name.label("category_name")
    ).outerjoin(
        categories,
        products.c.category_id == categories.c.id
    ).where(
        condition
    ).order_by(
        score.desc(),
        products.c.id
    ).limit(request.limit)

    count_stmt = select(
        func.count()
    ).select_from(products).where(condition)

    if not query:
        rows = []
        total = 0
    else:
        with engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            total = conn.execute(count_stmt).scalar()

    return {
        "search_id": str(uuid4()),
        "query": request.query,
        "normalized_query": query,
        "mode": "baseline",
        "total": total,
        "products": [dict(row) for row in rows],
        "recommendations": [],
        "alternatives": [],
        "related_queries": [],
        "processing_time_ms": round(
            (perf_counter() - started) * 1000, 2
        )
    }