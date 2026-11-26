from fastapi import FastAPI
from backend.app.catalog import router as catalog_router
from backend.app.baseline import router as baseline_router

app = FastAPI(
    title="SoftSearch API",
    version="0.1.0"
)

app.include_router(catalog_router)
app.include_router(baseline_router)

@app.get("/")
def home():
    return {"message": "SoftSearch API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def database_health():
    from backend.app.database import check_connection
    from fastapi import HTTPException

    try:
        if check_connection():
            return {"status": "ok", "database": "connected"}
    except Exception:
        pass

    raise HTTPException(
        status_code=503,
        detail="Database unavailable"
    )