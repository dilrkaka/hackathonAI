"""Поисковик: BM25 + синонимы + опечатки + проверка характеристик + допродажи.

Как строится ответ на запрос (search_full):
  1. разбор запроса: опечатки, раскладка, синонимы (normalize.py, typos.py);
  2. BM25 по ВСЕМ товарам, затем из каждого семейства (group_id) берём лучший товар;
  3. пересчёт оценки: недоступные товары хуже, совпадение характеристик плюс/минус;
  4. ответ: до MAIN_SLOTS точных совпадений + допродажи + (если мало) похожие.
Каждый результат — из РАЗНОГО семейства (так просили организаторы).
"""
from .bm25 import BM25
from .characteristics import check_product, extract_requirements, strip_term
from .normalize import analyze_query, index_tokens
from .query_log import DEFAULT_LOG, log_query
from .recommend import cross_sell
from .typos import SpellFixer

UNAVAILABLE_PENALTY = 0.6   # товар недоступен / цена 0 -> оценка x0.6 (2-й приоритет)
PHRASE_BONUS = 1.3          # слова запроса стоят в названии подряд
CANDIDATES = 50             # сколько семейств перепроверяем подробно
MAIN_SLOTS = 3              # максимум «точных» товаров; остальное — допродажи/похожие


def doc_text(o):
    # название и вендор повторяем: так они весят больше описания
    return " ".join([o.get("name", "")] * 3 + [o.get("vendor", "")] * 2 +
                    [o.get("vendor_slug", ""), o.get("category_path", ""), o.get("description", "")])


def family_of(o):
    return o.get("group_id") or o["id"]


def is_orderable(o):
    return bool(o.get("available", True)) and o.get("price", 0) > 0


def _coverage(analysis, doc_set):
    """Какая доля слов запроса есть в товаре (с учётом синонимов и склеек соседей)."""
    groups, joined = analysis["groups"], analysis["joined"]
    if not groups:
        return 0.0
    ok = 0
    for i, g in enumerate(groups):
        if any(v in doc_set for v in g):
            ok += 1
        elif (i > 0 and joined[i - 1] in doc_set) or (i < len(joined) and joined[i] in doc_set):
            ok += 1
    return ok / len(groups)


class SearchEngine:
    def __init__(self, offers, log_path=DEFAULT_LOG):
        self.offers = offers
        self.log_path = log_path
        self.bm25 = BM25([index_tokens(doc_text(o)) for o in offers])
        self.fixer = SpellFixer({t: len(p) for t, p in self.bm25.inv.items()})

    # ---------- ядро ----------
    def _rank(self, analysis, reqs, exclude=frozenset(), phrase=""):
        tokens = [v for g in analysis["groups"] for v in g] + analysis["joined"]
        best = {}  # семейство -> (оценка, индекс товара): лучший товар семейства
        for i, score in self.bm25.search(tokens, k=None):  # k=None: без обрезки до 200!
            o = self.offers[i]
            fam = family_of(o)
            if fam in exclude:
                continue
            adj = score if is_orderable(o) else score * UNAVAILABLE_PENALTY
            if fam not in best or adj > best[fam][0]:
                best[fam] = (adj, i)
        top = sorted(best.values(), reverse=True)[:CANDIDATES]
        results = []
        for adj, i in top:
            o = self.offers[i]
            doc_set = set(index_tokens(doc_text(o)))
            checks, factor = check_product(o, reqs)
            if phrase and phrase in " ".join(index_tokens(o.get("name", ""))):
                factor *= PHRASE_BONUS
            results.append({**o, "family": family_of(o), "score": round(adj * factor, 3),
                            "coverage": round(_coverage(analysis, doc_set), 2), "checks": checks})
        results.sort(key=lambda r: -r["score"])
        return results

    def rank_text(self, text, exclude=frozenset()):
        """Поиск по готовой строке (нужен для допродаж)."""
        a = analyze_query(strip_term(text), self.fixer)
        return self._rank(a, extract_requirements(text), exclude, " ".join(g[0] for g in a["groups"]))

    # ---------- публичный интерфейс ----------
    def search_full(self, query: str, top_k: int = 4, log: bool = True):
        a = analyze_query(strip_term(query), self.fixer)
        reqs = extract_requirements(query)
        phrase = " ".join(g[0] for g in a["groups"])
        ranked = self._rank(a, reqs, phrase=phrase)

        full = [r for r in ranked if r["coverage"] >= 1 and "mismatch" not in r["checks"].values()]
        rest = [r for r in ranked if r not in full]
        for r in full:
            r["role"], r["reason"] = "match", "Полностью соответствует запросу"
        if full:
            block = full[:MAIN_SLOTS]
            tail = full[MAIN_SLOTS:] + rest
        else:  # точных нет — показываем лучшие частичные как «похожие»
            block = rest[:2]
            tail = rest[2:]
        for r in block:
            if "role" not in r:
                r["role"], r["reason"] = "alternative", "Совпадает частично или не подходит по характеристикам"
                if "mismatch" in r["checks"].values():
                    bad = [k for k, v in r["checks"].items() if v == "mismatch"]
                    r["reason"] = "Не совпадает: " + ", ".join(bad)
        results = list(block)
        used = {r["family"] for r in results}
        results += cross_sell(self, results[0] if results else None, used, top_k - len(results))
        used = {r["family"] for r in results}
        for r in tail:  # добираем до top_k, если допродаж не хватило
            if len(results) >= top_k:
                break
            if r["family"] not in used:
                r.setdefault("role", "alternative")
                r.setdefault("reason", "Похожий товар")
                results.append(r)
                used.add(r["family"])
        results = results[:top_k]

        note = ""
        if not results:
            note = "По запросу ничего не найдено."
        elif len(results) < top_k:
            note = f"Найдено товаров: {len(results)} (меньше {top_k}) — остальные не подходят под запрос."
        elif not full:
            note = "Точных совпадений нет, показаны ближайшие варианты."
        out = {
            "query": query,
            "corrected": " ".join(g[0] for g in a["groups"]),
            "fixes": a["fixes"],
            "requirements": {k: sorted(v) if isinstance(v, set) else v for k, v in reqs.items()},
            "note": note,
            "results": results,
        }
        if log and self.log_path:
            log_query({"query": query, "corrected": out["corrected"], "fixes": a["fixes"],
                       "n_results": len(results), "n_main": sum(r["role"] == "match" for r in results),
                       "top": [r["name"][:60] for r in results]}, self.log_path)
        return out

    def search(self, query: str, top_k: int = 4):
        """Короткая версия: только список товаров (без записи в журнал)."""
        return self.search_full(query, top_k, log=False)["results"]
