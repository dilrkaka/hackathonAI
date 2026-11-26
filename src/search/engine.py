"""Базовый поисковик: BM25 по offers + схлопывание в группы (минимум N разных товаров)."""
from .bm25 import BM25
from .normalize import index_tokens, normalize_query


def doc_text(o):
    # название и вендор повторяем: так они весят больше описания
    return " ".join([o.get("name", "")] * 3 + [o.get("vendor", "")] * 2 +
                    [o.get("vendor_slug", ""), o.get("category_path", ""), o.get("description", "")])


class SearchEngine:
    def __init__(self, offers):
        self.offers = offers
        self.bm25 = BM25([index_tokens(doc_text(o)) for o in offers])

    def search(self, query: str, top_k: int = 4):
        hits = self.bm25.search(normalize_query(query), k=200)
        seen, results = set(), []
        for i, score in hits:
            o = self.offers[i]
            key = o.get("group_id") or o["id"]
            if key in seen:  # один товар (группа) — один раз в выдаче
                continue
            seen.add(key)
            results.append({**o, "score": round(score, 3)})
            if len(results) == top_k:
                break
        return results
