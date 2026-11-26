"""Программная проверка характеристик: платформа, срок лицензии, совместимость.

Организаторы ждут именно программную проверку (не «на глаз» и не LLM), поэтому
правила простые и прозрачные: берём требования из запроса и сверяем с полями товара.
"""
import re

from .normalize import tokenize

# платформа -> слова, по которым её узнаём (в запросе и в карточке товара)
PLATFORMS = {
    "windows": {"windows", "винда", "винды", "винд", "win"},
    "linux": {"linux", "линукс", "astra", "астра", "astralinux"},
    "macos": {"macos", "mac", "мак"},
    "android": {"android", "андроид"},
    "ios": {"ios", "iphone", "айфон"},
}


def platforms_of(text: str):
    toks = set(tokenize(text))
    return {p for p, words in PLATFORMS.items() if toks & words}


def months_of(text: str):
    """«на 3 года» / «12 месяцев» / «1 год» -> число месяцев, иначе None."""
    t = text.lower()
    m = re.search(r"(\d+)\s*(лет|год|года|г\.?)(?![а-я])", t)
    if m:
        return int(m.group(1)) * 12
    m = re.search(r"(\d+)\s*(мес)", t)
    if m:
        return int(m.group(1))
    if re.search(r"\bна год\b", t):
        return 12
    return None


def strip_term(query: str) -> str:
    """Убирает из запроса «на 3 года» — это характеристика, а не слово для поиска по тексту."""
    q = re.sub(r"(на\s+)?\d+\s*(лет|года|год|г\.?|мес[а-я]*)(?![а-я])", " ", query.lower())
    return re.sub(r"\bна год\b", " ", q)


def extract_requirements(query: str):
    reqs = {}
    pl = platforms_of(query)
    if pl:
        reqs["platform"] = pl
    mo = months_of(query)
    if mo:
        reqs["term_months"] = mo
    return reqs


def _product_platforms(p):
    return platforms_of(p.get("params", {}).get("platform", "") + " " + p.get("name", ""))


def check_product(p, reqs):
    """Возвращает ({'platform': 'ok'|'mismatch'|'unknown', ...}, множитель_оценки)."""
    checks, factor = {}, 1.0
    if "platform" in reqs:
        have = _product_platforms(p)
        if not have:
            checks["platform"] = "unknown"
        elif have & reqs["platform"]:
            checks["platform"] = "ok"
        else:
            checks["platform"] = "mismatch"
    if "term_months" in reqs:
        raw = p.get("params", {}).get("term", "") + " " + p.get("name", "")
        have = months_of(raw)
        if have is None:
            checks["term"] = "unknown"
        elif have == reqs["term_months"]:
            checks["term"] = "ok"
        else:
            checks["term"] = "mismatch"
    for v in checks.values():
        factor *= {"ok": 1.15, "mismatch": 0.5, "unknown": 1.0}[v]
    return checks, factor


def is_compatible(a, b):
    """Можно ли предлагать b вместе с a (допродажа). Если платформа неизвестна — не блокируем."""
    pa, pb = _product_platforms(a), _product_platforms(b)
    return not pa or not pb or bool(pa & pb)
