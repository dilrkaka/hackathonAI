from html import unescape

from fastapi import APIRouter, Query
from sqlalchemy import select, func, or_, case

from backend.app.database import engine
from backend.app.models import products
from src.search.normalize import SYNONYMS

router = APIRouter(
    prefix="/api",
    tags=["Suggestions"]
)


@router.get("/suggestions")
def get_suggestions(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(8, ge=1, le=20)
):
    query = q.strip().lower()

    if len(query) < 2:
        return {"suggestions": []}

    suggestions = []
    seen = set()

    def add(value):
        if not value:
            return

        value = unescape(value).strip()
        key = value.lower()

        if key not in seen and len(suggestions) < limit:
            seen.add(key)
            suggestions.append(value)

    for word, synonym in SYNONYMS.items():
        if word.startswith(query):
            add(synonym)

    escaped = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    prefix = f"{escaped}%"
    pattern = f"%{escaped}%"

    vendor_stmt = (
        select(products.c.vendor)
        .where(
            products.c.vendor.ilike(
                prefix, escape="\\"
            )
        )
        .distinct()
        .order_by(products.c.vendor)
        .limit(limit)
    )

    score = case(
        (
            products.c.name.ilike(
                prefix, escape="\\"
            ),
            2
        ),
        else_=1
    )

    product_stmt = (
        select(products.c.name)
        .where(
            products.c.name.ilike(
                pattern, escape="\\"
            )
        )
        .order_by(
            score.desc(),
            products.c.available.desc().nulls_last(),
            func.length(products.c.name)
        )
        .limit(limit * 3)
    )

    with engine.connect() as conn:
        for vendor in conn.execute(vendor_stmt).scalars():
            add(vendor)

        for name in conn.execute(product_stmt).scalars():
            add(name)

    return {
        "query": q,
        "suggestions": suggestions
    }