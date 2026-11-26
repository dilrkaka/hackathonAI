from fastapi import FastAPI

app = FastAPI(
    title="SoftSearch API",
    version="0.1.0"
)


@app.get("/")
def home():
    return {"message": "SoftSearch API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}