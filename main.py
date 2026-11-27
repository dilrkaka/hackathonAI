import os
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def home():
    return "Hackathon server is running!"

@app.route("/health")
def health():
    return {"status": "ok"}

INDEX_PATH = "data/processed/offers.jsonl"
_engine = None


def get_engine():
    """Поисковик грузим при первом запросе (а не при старте сервера)."""
    global _engine
    if _engine is None:
        if not os.path.exists(INDEX_PATH):
            return None
        from src.search.catalog import load_jsonl
        from src.search.engine import SearchEngine
        _engine = SearchEngine(load_jsonl(INDEX_PATH))
    return _engine


@app.route("/api/search")
def api_search():
    """Пример: /api/search?q=kaspersky&top_k=4"""
    q = request.args.get("q", "").strip()
    if not q:
        return {"error": "Пустой запрос. Добавьте ?q=..."}, 400
    engine = get_engine()
    if engine is None:
        return {"error": "Индекс не найден. Сначала: python scripts/build_index.py <xml>"}, 503
    out = engine.search_full(q, top_k=int(request.args.get("top_k", 4)))
    for r in out["results"]:  # описания длинные — в ответе обрезаем
        r["description"] = r.get("description", "")[:300]
    return jsonify(out)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
