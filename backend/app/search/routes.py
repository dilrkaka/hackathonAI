from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from backend.app.search.loader import get_search_engine
from backend.app.analytics.service import record_search

router = APIRouter(
    prefix="/api/search",
    tags=["Search"]
)


class SmartSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=4, ge=4, le=20)
    request_id: str | None = Field(default=None, max_length=100)
    log: bool = True


def execute_search(query, limit, request_id=None, log=True):
    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Empty search query"
        )

    started = perf_counter()

    search_engine = get_search_engine()

    out = search_engine.search_full(
        query,
        top_k=limit,
        log=False
    )

    results = out["results"]

    result = {
        "search_id": request_id or str(uuid4()),
        "query": query,
        "normalized_query": out["corrected"],
        "mode": "smart",
        "total": len(results),
        "products": [
            r for r in results
            if r["role"] == "match"
        ],
        "recommendations": [
            r for r in results
            if r["role"] == "upsell"
        ],
        "alternatives": [
            r for r in results
            if r["role"] == "alternative"
        ],
        "results": results,
        "fixes": out["fixes"],
        "requirements": out["requirements"],
        "note": out["note"],
        "processing_time_ms": round(
            (perf_counter() - started) * 1000, 2
        )
    }

    if log:
        record_search(result)

    return result


@router.post("/smart")
def smart_search(request: SmartSearchRequest):
    return execute_search(
        request.query,
        request.limit,
        request.request_id,
        request.log
    )


@router.get("")
def search(
    q: str = Query(min_length=1, max_length=500),
    top_k: int = Query(4, ge=4, le=20)
):
    return execute_search(q, top_k)