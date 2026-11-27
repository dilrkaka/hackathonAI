from html import unescape
from threading import Lock
from urllib.parse import urlparse

from sqlalchemy import select

from backend.app.database import engine
from backend.app.models import products, categories
from src.search.engine import SearchEngine
from src.search.catalog import PARAM_KEYS

_search_engine = None
_lock = Lock()


def clean(value):
    return unescape(str(value or ""))


def category_path(category_id, cats):
    path = []
    visited = set()

    while category_id in cats and category_id not in visited:
        visited.add(category_id)
        category = cats[category_id]

        path.append(clean(category["name"]))
        category_id = category["parent_id"]

    return " > ".join(reversed(path))


def load_products():
    offers = []

    with engine.connect() as conn:
        cats = {
            row["id"]: dict(row)
            for row in conn.execute(
                select(categories)
            ).mappings()
        }

        rows = conn.execution_options(
            stream_results=True
        ).execute(select(products)).mappings()

        for row in rows:
            product = dict(row)

            for key in ("name", "vendor", "description", "vendor_code"):
                product[key] = clean(product.get(key))

            product["price"] = float(product["price"] or 0)
            product["old_price"] = float(product["old_price"] or 0)

            path = category_path(
                product["category_id"], cats
            )

            product["category_path"] = path
            product["category_name"] = path.split(" > ")[-1]

            url = urlparse(product["url"] or "")
            parts = url.path.strip("/").split("/")
            product["vendor_slug"] = parts[0]

            raw_params = product["params"] or {}
            params = {}

            for ru, en in PARAM_KEYS.items():
                values = raw_params.get(ru, [])

                if isinstance(values, str):
                    values = [values]

                values = [
                    clean(v) for v in values
                    if v and v != "другое или отсутствует"
                ]

                if values:
                    params[en] = " ".join(values)

            product["raw_params"] = raw_params
            product["params"] = params

            offers.append(product)

    return offers


def get_search_engine():
    global _search_engine

    if _search_engine is None:
        with _lock:
            if _search_engine is None:
                offers = load_products()
                print(f"Building index: {len(offers)} products", flush=True)

                _search_engine = SearchEngine(
                    offers,
                    log_path=None
                )

                print("Search index ready", flush=True)

    return _search_engine