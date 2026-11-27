
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.search.loader import get_search_engine

QUERIES = [
    "сервер",
    "ноут для программиста",
    "рабочее место программиста",
    "защита компьютера от вирусов",
    "антивирс",
    "фотошоп",
    "ноутбук до 50000",
    "абракадабраззз",
    "программа для монтажа видео",
]

engine = get_search_engine()

for query in sys.argv[1:] or QUERIES:
    out = engine.search_full(
        query,
        top_k=4,
        log=False
    )

    results = out["results"]
    popular = out.get("popular_recommendations", [])
    intent = out.get("intent")

    matches = sum(
        r["role"] == "match" for r in results
    )

    print("\n" + "=" * 70)
    print("Запрос:", query)
    print("Намерение:", intent)
    print("Основных совпадений:", matches)
    print("Всего результатов:", len(results))
    print("Популярных рекомендаций:", len(popular))

    for r in results:
        print(f'  [{r["role"]}] {r["name"]}')
        print("    Категория:", r.get("category_path"))
        print("    Причина:", r.get("reason"))

    if popular:
        print("\nПопулярные товары:")
        for r in popular:
            print("  -", r.get("name"))

    if out.get("note"):
        print("\nПримечание:", out["note"])
