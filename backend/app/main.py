from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.app.catalog import router as catalog_router
from backend.app.baseline import router as baseline_router
from backend.app.search.routes import router as smart_router
from backend.app.search.suggestions import router as suggestions_router
from backend.app.recommendations.routes import router as recommendations_router

app = FastAPI(
    title="SoftSearch API",
    version="0.1.0"
)

app.include_router(catalog_router)
app.include_router(baseline_router)
app.include_router(smart_router)
app.include_router(suggestions_router)
app.include_router(recommendations_router)


@app.get("/")
def home():
    return RedirectResponse("/store/")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    from backend.app.database import check_connection

    try:
        if check_connection():
            return {
                "status": "ok",
                "database": "connected"
            }
    except Exception:
        pass

    raise HTTPException(
        status_code=503,
        detail="Database unavailable"
    )


FRONTEND_DIR = (
    Path(__file__).resolve().parents[2] / "frontend"
)

app.mount(
    "/store",
    StaticFiles(
        directory=str(FRONTEND_DIR),
        html=True
    ),
    name="frontend"
)