from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.app.database import engine
from backend.app.analytics.models import search_logs, user_events

router = APIRouter(
    prefix="/api",
    tags=["Analytics"]
)


class EventRequest(BaseModel):
    type: Literal[
        "search",
        "click",
        "product_view",
        "buy_click",
        "compare"
    ]

    query: str | None = Field(default=None, max_length=500)
    mode: Literal["baseline", "smart"] | None = None

    product_id: str | None = Field(default=None, max_length=100)
    position: int | None = Field(default=None, ge=1, le=100)
    results_count: int | None = Field(default=None, ge=0)

    baseline_count: int | None = Field(default=None, ge=0)
    smart_count: int | None = Field(default=None, ge=0)

    source: str | None = Field(default=None, max_length=100)
    from_product_id: str | None = Field(default=None, max_length=100)
    search_id: str | None = Field(default=None, max_length=100)
    event_id: str | None = Field(default=None, max_length=100)


@router.post("/events", status_code=201)
def create_event(event: EventRequest):
    event_id = event.event_id or str(uuid4())

    with engine.begin() as conn:
        stmt = pg_insert(user_events).values(
                id=event_id,
                type=event.type,
                query=event.query,
                mode=event.mode,
                product_id=event.product_id,
                position=event.position,
                payload=event.model_dump()
            ).on_conflict_do_nothing(index_elements=[user_events.c.id])
        conn.execute(stmt)

    return {
        "status": "ok",
        "event_id": event_id
    }


def count_rate(value, total):
    if not total:
        return None

    return round(value / total * 100, 2)


@router.get("/analytics")
def analytics():
    mode_stats = {}

    query_key = func.lower(
        func.trim(search_logs.c.query)
    )

    with engine.connect() as conn:

        total_searches = conn.execute(
            select(func.count())
            .select_from(search_logs)
        ).scalar()

        top_queries = conn.execute(
            select(
                query_key.label("query"),
                func.count().label("count")
            )
            .group_by(query_key)
            .order_by(func.count().desc())
            .limit(10)
        ).mappings().all()

        zero_results = conn.execute(
            select(
                query_key.label("query"),
                func.count().label("count")
            )
            .where(search_logs.c.returned_count == 0)
            .group_by(query_key)
            .order_by(func.count().desc())
            .limit(20)
        ).mappings().all()

        weak_queries = conn.execute(
            select(
                query_key.label("query"),
                func.count().label("count")
            )
            .where(
                search_logs.c.mode == "smart",
                search_logs.c.match_count == 0,
                search_logs.c.returned_count > 0
            )
            .group_by(query_key)
            .order_by(func.count().desc())
            .limit(20)
        ).mappings().all()

        for mode in ("baseline", "smart"):
            condition = search_logs.c.mode == mode

            total = conn.execute(
                select(func.count())
                .select_from(search_logs)
                .where(condition)
            ).scalar()

            zero = conn.execute(
                select(func.count())
                .select_from(search_logs)
                .where(
                    condition,
                    search_logs.c.returned_count == 0
                )
            ).scalar()

            four = conn.execute(
                select(func.count())
                .select_from(search_logs)
                .where(
                    condition,
                    search_logs.c.returned_count >= 4
                )
            ).scalar()

            avg_time = conn.execute(
                select(
                    func.avg(search_logs.c.processing_time_ms)
                )
                .where(condition)
            ).scalar()

            mode_stats[mode] = {
                "searches": total,
                "zero_results": zero,
                "zero_rate": count_rate(zero, total),
                "non_empty_rate": count_rate(total - zero, total),
                "four_results_rate": count_rate(four, total),
                "avg_time_ms": (
                    round(float(avg_time), 2)
                    if avg_time is not None
                    else None
                )
            }

        event_rows = conn.execute(
            select(
                user_events.c.type,
                func.count().label("count")
            )
            .group_by(user_events.c.type)
        ).mappings().all()

        popular_products = conn.execute(
            select(
                user_events.c.product_id,
                func.count().label("count")
            )
            .where(
                user_events.c.type == "click",
                user_events.c.product_id.is_not(None)
            )
            .group_by(user_events.c.product_id)
            .order_by(func.count().desc())
            .limit(10)
        ).mappings().all()

    events = {
        row["type"]: row["count"]
        for row in event_rows
    }

    baseline = mode_stats["baseline"]
    smart = mode_stats["smart"]

    comparison = None

    if baseline["searches"] and smart["searches"]:
        comparison = {
            "labels": [
                "Непустая выдача",
                "4 и более товаров",
                "Пустая выдача"
            ],
            "baseline": [
                baseline["non_empty_rate"],
                baseline["four_results_rate"],
                baseline["zero_rate"]
            ],
            "smart": [
                smart["non_empty_rate"],
                smart["four_results_rate"],
                smart["zero_rate"]
            ]
        }

    return {
        "total_searches": total_searches,
        "top_queries": [dict(row) for row in top_queries],
        "zero_results": [dict(row) for row in zero_results],
        "weak_queries": [dict(row) for row in weak_queries],
        "modes": mode_stats,
        "comparison": comparison,
        "events": {
            "clicks": events.get("click", 0),
            "product_views": events.get("product_view", 0),
            "buy_clicks": events.get("buy_click", 0),
            "comparisons": events.get("compare", 0)
        },
        "popular_products": [
            dict(row) for row in popular_products
        ]
    }