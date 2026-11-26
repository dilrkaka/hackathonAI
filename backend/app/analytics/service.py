import logging

from backend.app.database import engine
from backend.app.analytics.models import metadata, search_logs

logger = logging.getLogger(__name__)


def init_analytics():
    metadata.create_all(engine)


def record_search(result):
    items = result.get("results", result.get("products", []))
    mode = result["mode"]

    match_count = None

    if mode == "smart":
        match_count = sum(
            p.get("role") == "match"
            for p in items
        )

    query = result["query"].strip()

    if not query:
        return

    try:
        with engine.begin() as conn:
            conn.execute(
                search_logs.insert().values(
                    id=result["search_id"],
                    query=query,
                    normalized_query=result.get("normalized_query"),
                    mode=mode,
                    total=result["total"],
                    returned_count=len(items),
                    match_count=match_count,
                    processing_time_ms=result.get(
                        "processing_time_ms"
                    ),
                    result_ids=[
                        str(p["id"]) for p in items
                    ],
                    fixes=result.get("fixes", [])
                )
            )

    except Exception:
        logger.exception("Failed to save search log")