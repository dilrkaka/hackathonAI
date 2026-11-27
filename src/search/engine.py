
"""Поисковик: BM25 + синонимы + опечатки + характеристики + допродажи."""

from .bm25 import BM25
from .characteristics import check_product, extract_requirements, strip_term
from .intent import (
    detect_intent,
    intent_hit,
    intent_match_type,
    strip_consumed,
)
from .normalize import analyze_query, index_tokens, tokenize
from .query_log import DEFAULT_LOG, log_query
from .recommend import cross_sell
from .typos import SpellFixer


UNAVAILABLE_PENALTY = 0.6
PHRASE_BONUS = 1.3
CANDIDATES = 50
MAIN_SLOTS = 3
MIN_RESULTS = 4
INTENT_BONUS = 1.6
INTENT_OFFTOPIC = 0.6
SERVER_PENALTY = 0.6
LAPTOP_PRIORITY_BONUS = 3.0

FILL_QUERIES = [
    "антивирус",
    "windows",
    "office",
    "резервное копирование",
]


def doc_text(o):
    return " ".join(
        [o.get("name", "")] * 3
        + [o.get("vendor", "")] * 2
        + [
            o.get("vendor_slug", ""),
            o.get("category_path", ""),
            o.get("description", ""),
        ]
    )


def family_of(o):
    return o.get("group_id") or o["id"]


def is_orderable(o):
    return bool(o.get("available", True)) and o.get("price", 0) > 0


def _is_server_product(o):
    return any(
        token.startswith(("сервер", "server"))
        for token in tokenize(o.get("name", ""))
    )


def _coverage(analysis, doc_set):
    """Определяет, какая доля слов запроса найдена в товаре."""
    groups = analysis["groups"]
    joined = analysis["joined"]

    if not groups:
        return 0.0

    ok = 0

    for i, group in enumerate(groups):
        if any(value in doc_set for value in group):
            ok += 1
        elif (
            (i > 0 and joined[i - 1] in doc_set)
            or (i < len(joined) and joined[i] in doc_set)
        ):
            ok += 1

    return ok / len(groups)


class SearchEngine:
    def __init__(self, offers, log_path=DEFAULT_LOG):
        self.offers = offers
        self.log_path = log_path

        self.bm25 = BM25([
            index_tokens(doc_text(offer))
            for offer in offers
        ])

        self.fixer = SpellFixer({
            token: len(postings)
            for token, postings in self.bm25.inv.items()
        })

    def _rank(
        self,
        analysis,
        reqs,
        exclude=frozenset(),
        phrase="",
        intent=None
    ):
        tokens = [
            value
            for group in analysis["groups"]
            for value in group
        ] + analysis["joined"]

        if intent:
            tokens += index_tokens(" ".join(intent["expand"]))

        best = {}

        for i, score in self.bm25.search(tokens, k=None):
            offer = self.offers[i]

            # Если ищут Docker, исключаем товары,
            # в названии которых прямо указано отсутствие Docker.
            query_has_docker = any(
                token.startswith("docker")
                for token in tokens
            )

            offer_name = offer.get("name", "").lower()

            if query_has_docker and (
                    "w/o docker" in offer_name
                    or "without docker" in offer_name
            ):
                continue

            family = family_of(offer)

            if family in exclude:
                continue

            adjusted_score = (
                score
                if is_orderable(offer)
                else score * UNAVAILABLE_PENALTY
            )

            if (
                family not in best
                or adjusted_score > best[family][0]
            ):
                best[family] = (adjusted_score, i)

        top = sorted(
            best.values(),
            reverse=True
        )[:CANDIDATES]

        results = []

        for adjusted_score, i in top:
            offer = self.offers[i]

            document_tokens = set(
                index_tokens(doc_text(offer))
            )

            checks, factor = check_product(offer, reqs)

            if (
                phrase
                and phrase in " ".join(
                    index_tokens(offer.get("name", ""))
                )
            ):
                factor *= PHRASE_BONUS

            hit = intent_hit(offer, intent)

            if intent:
                factor *= (
                    INTENT_BONUS
                    if hit
                    else INTENT_OFFTOPIC
                )

                # При запросе ноутбука физические ноутбуки
                # получают приоритет над программами.
                if intent["name"] == "dev_laptop":
                    match_type = intent_match_type(offer, intent)

                    if (
                        intent.get("mode") == "laptop"
                        and match_type == "laptop"
                    ):
                        factor *= LAPTOP_PRIORITY_BONUS

                # Для серверного запроса серверные товары не штрафуем.
                if (
                    intent["name"] != "server"
                    and _is_server_product(offer)
                ):
                    factor *= SERVER_PENALTY

            if analysis["groups"]:
                coverage = _coverage(
                    analysis,
                    document_tokens
                )
            else:
                coverage = 1.0 if hit else 0.0

            results.append({
                **offer,
                "family": family_of(offer),
                "score": round(
                    adjusted_score * factor,
                    3
                ),
                "coverage": round(coverage, 2),
                "checks": checks,
                "intent_hit": hit,
            })

        results.sort(
            key=lambda result: -result["score"]
        )

        return results

    def rank_text(self, text, exclude=frozenset()):
        analysis = analyze_query(
            strip_term(text),
            self.fixer
        )

        return self._rank(
            analysis,
            extract_requirements(text),
            exclude,
            " ".join(
                group[0]
                for group in analysis["groups"]
            )
        )

    def _as_result(self, offer, role, reason):
        return {
            **offer,
            "family": family_of(offer),
            "score": 0.0,
            "coverage": 0.0,
            "checks": {},
            "intent_hit": False,
            "role": role,
            "reason": reason,
        }

    def _fill(self, results, top_k, reqs):
        used = {
            result["family"]
            for result in results
        }

        def is_ok(offer):
            checks, _ = check_product(offer, reqs)

            return (
                family_of(offer) not in used
                and "mismatch" not in checks.values()
            )

        def add(result):
            results.append(result)
            used.add(result["family"])

        if results:
            category = results[0].get("category_path")

            same_category = [
                offer
                for offer in self.offers
                if (
                    category
                    and offer.get("category_path") == category
                    and is_ok(offer)
                )
            ]

            same_category.sort(
                key=lambda offer: not is_orderable(offer)
            )

            for offer in same_category:
                if len(results) >= top_k:
                    return

                if family_of(offer) not in used:
                    add(
                        self._as_result(
                            offer,
                            "alternative",
                            "Из той же категории"
                        )
                    )

        for query in FILL_QUERIES:
            if len(results) >= top_k:
                return

            candidates = self.rank_text(
                query,
                exclude=used
            )

            for result in candidates:
                if len(results) >= top_k:
                    return

                if (
                    result["family"] not in used
                    and is_ok(result)
                    and result["coverage"] >= 1
                ):
                    result["role"] = "alternative"
                    result["reason"] = "Популярный товар"

                    add(result)
                    break

        for offer in self.offers:
            if len(results) >= top_k:
                return

            if (
                is_orderable(offer)
                and is_ok(offer)
            ):
                add(
                    self._as_result(
                        offer,
                        "alternative",
                        "Рекомендуем посмотреть"
                    )
                )

    def search_full(self, query: str, top_k: int = 4, log: bool = True):
        top_k = max(top_k, MIN_RESULTS)

        intent = detect_intent(query)

        text = strip_consumed(
            strip_term(query),
            intent
        )

        analysis = analyze_query(
            text,
            self.fixer
        )

        reqs = extract_requirements(query)

        phrase = " ".join(
            group[0]
            for group in analysis["groups"]
        )

        ranked = self._rank(
            analysis,
            reqs,
            phrase=phrase,
            intent=intent
        )

        # Основные результаты должны быть релевантными.
        full = [
            result
            for result in ranked
            if (
                result["coverage"] >= 1
                and "mismatch" not in result["checks"].values()
                and (
                    not intent
                    or result["intent_hit"]
                )
            )
        ]

        rest = [
            result
            for result in ranked
            if result not in full
        ]

        for result in full:
            result["role"] = "match"
            result["reason"] = (
                "Подходит под задачу: " + intent["label"]
                if intent
                else "Полностью соответствует запросу"
            )

        if full:
            block = full[:MAIN_SLOTS]
            tail = full[MAIN_SLOTS:] + rest
        else:
            block = rest[:2]
            tail = rest[2:]

        for result in block:
            if "role" not in result:
                result["role"] = "alternative"
                result["reason"] = (
                    "Совпадает частично или не подходит "
                    "по характеристикам"
                )

                if "mismatch" in result["checks"].values():
                    bad = [
                        key
                        for key, value in result["checks"].items()
                        if value == "mismatch"
                    ]

                    result["reason"] = (
                        "Не совпадает: " + ", ".join(bad)
                    )

        results = list(block)

        used = {
            result["family"]
            for result in results
        }

        # Допродажи добавляются только к подходящему товару.
        if full:
            upsells = cross_sell(
                self,
                full[0],
                used,
                top_k - len(results),
                intent=intent,
                want_platforms=reqs.get("platform")
            )

            results += upsells

        used = {
            result["family"]
            for result in results
        }

        for result in tail:
            if len(results) >= top_k:
                break

            if result["family"] not in used:
                result.setdefault(
                    "role",
                    "alternative"
                )
                result.setdefault(
                    "reason",
                    "Похожий товар"
                )

                results.append(result)
                used.add(result["family"])

        results = results[:top_k]

        # Популярные товары показываются отдельно от поиска.
        popular_recommendations = []

        if not full:
            popular = [
                offer
                for offer in self.offers
                if (
                    offer.get("is_popular")
                    or offer.get("popularity", 0) > 0
                )
            ]

            popular.sort(
                key=lambda offer: offer.get("popularity", 0),
                reverse=True
            )

            seen = set()

            for offer in popular:
                family = family_of(offer)

                if (
                    family in seen
                    or not is_orderable(offer)
                ):
                    continue

                seen.add(family)

                popular_recommendations.append(
                    self._as_result(
                        offer,
                        "popular",
                        "Популярный товар — не является результатом поиска"
                    )
                )

                if len(popular_recommendations) >= top_k:
                    break

        if results and len(results) < top_k:
            self._fill(
                results,
                top_k,
                reqs
            )

        results = results[:top_k]

        if not full:
            note = (
                "По вашему запросу ничего не найдено "
                "среди подходящих товаров. Показаны ближайшие "
                "варианты и отдельно популярные товары."
            )
        elif len(results) < top_k:
            note = (
                f"Найдено товаров: {len(results)} "
                f"(меньше {top_k}) — в каталоге больше нет подходящих."
            )
        else:
            note = ""

        out = {
            "query": query,
            "corrected": (
                " ".join(
                    group[0]
                    for group in analysis["groups"]
                )
                or query.lower().strip()
            ),
            "fixes": analysis["fixes"],
            "intent": (
                {
                    "name": intent["name"],
                    "label": intent["label"]
                }
                if intent
                else None
            ),
            "requirements": {
                key: (
                    sorted(value)
                    if isinstance(value, set)
                    else value
                )
                for key, value in reqs.items()
            },
            "note": note,
            "results": results,
            "popular_recommendations": popular_recommendations,
        }

        if log and self.log_path:
            main_count = sum(
                result["role"] == "match"
                for result in results
            )

            log_query(
                {
                    "query": query,
                    "corrected": out["corrected"],
                    "fixes": analysis["fixes"],
                    "intent": (
                        intent["name"]
                        if intent
                        else None
                    ),
                    "n_results": len(results),
                    "n_main": main_count,
                    "failed": main_count == 0,
                    "top": [
                        result["name"][:60]
                        for result in results
                    ],
                },
                self.log_path
            )

        return out

    def search(self, query: str, top_k: int = 4):
        return self.search_full(
            query,
            top_k,
            log=False
        )["results"]
