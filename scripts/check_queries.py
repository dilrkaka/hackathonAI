
"""Проверка результатов умного поиска на реальном каталоге.

Запуск:
python scripts/check_queries.py

Можно передать свои запросы:
python scripts/check_queries.py "сервер" "антивирус"
"""

import sys

sys.path.insert(0, ".")

from src.search.catalog import load_jsonl
from src.search.engine import SearchEngine


QUERIES = [
    "сервер",
    "ноут для программиста",
    "рабочее место программиста",
    "защита компьютера от вирусов",
]


engine = SearchEngine(
    load_jsonl("data/processed/offers.jsonl"),
    log_path=None
)

for query in (sys.argv[1:] or QUERIES):
    out = engine.search_full(
        query,
        top_k=4,
        log=False
    )

    print(
        f'\n=== {query}   '
        f'намерение: {out["intent"] and out["intent"]["label"]}   '
        f'товаров: {len(out["results"])}'
    )

    for result in out["results"]:
        print(
            f'  {result["role"]:<11} '
            f'{result["name"][:60]:<62} '
            f'[{result["category_path"][-40:]}]'
        )

        print(f'              почему: {result["reason"]}')

    if out["note"]:
        print("  примечание:", out["note"])
