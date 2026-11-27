from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from backend.app.database import engine
from backend.app.models import products, categories

router = APIRouter(prefix="/api", tags=["Catalog"])


@router.get("/products")
def get_products(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: str | None = None,
    vendor: str | None = None,
    available: bool | None = None
):
    stmt = select(
        products,
        categories.c.name.label("category_name")
    ).outerjoin(
        categories,
        products.c.category_id == categories.c.id
    )

    if category_id:
        stmt = stmt.where(
            products.c.category_id == category_id
        )

    if vendor:
        stmt = stmt.where(products.c.vendor == vendor)

    if available is not None:
        stmt = stmt.where(
            products.c.available == available
        )

    stmt = stmt.order_by(
        products.c.id
    ).limit(limit).offset(offset)

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return {
        "products": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset
    }


@router.get("/products/{product_id}")
def get_product(product_id: str):
    stmt = select(
        products,
        categories.c.name.label("category_name")
    ).outerjoin(
        categories,
        products.c.category_id == categories.c.id
    ).where(
        products.c.id == product_id
    )

    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return dict(row)


@router.get("/categories")
def get_categories(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    parent_id: str | None = None
):
    stmt = select(categories)

    if parent_id:
        stmt = stmt.where(
            categories.c.parent_id == parent_id
        )

    stmt = stmt.order_by(
        categories.c.name,
        categories.c.id
    ).limit(limit).offset(offset)

    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    return {
        "categories": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset
    }


@router.get("/catalog/stats")
def catalog_stats():
    with engine.connect() as conn:
        product_count = conn.execute(
            select(func.count()).select_from(products)
        ).scalar()

        category_count = conn.execute(
            select(func.count()).select_from(categories)
        ).scalar()

        available_count = conn.execute(
            select(func.count()).select_from(products)
            .where(products.c.available.is_(True))
        ).scalar()

        vendor_count = conn.execute(
            select(func.count(
                func.distinct(products.c.vendor)
            ))
        ).scalar()

    return {
        "products": product_count,
        "categories": category_count,
        "available_products": available_count,
        "vendors": vendor_count
    }