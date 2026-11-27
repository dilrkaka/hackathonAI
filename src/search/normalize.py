
"""Нормализация запросов, синонимы и исправление опечаток.

Синоним не заменяет исходное слово, а добавляется
к возможным вариантам поиска.
"""

import re


# Исправления, которые можно показывать пользователю.
DISPLAY_CORRECTIONS = {
    "антивирс": "антивирус",
    "антевирус": "антивирус",
    "каспрский": "касперский",
    "rfcgthcrbq": "касперский",
}


SYNONYMS = {
    "антивирь": "антивирус",
    "антивирс": "антивирус",
    "антевирус": "антивирус",
    "офис": "office",
    "винда": "windows",
    "винды": "windows",
    "вин": "windows",
    "астра": "astra",
    "линукс": "linux",
    "мтс": "мтс линк",
    "касперский": "kaspersky",
    "криптопро": "криптопро",
}


STOP_WORDS = {
    "на", "для", "и", "в", "с",
    "по", "от", "из", "или", "к"
}


# Раскладки клавиатуры.
_EN = "qwertyuiopasdfghjklzxcvbnm"
_RU = "йцукенгшщзфывапролдячсмить"

EN_TO_RU = dict(zip(_EN, _RU))
RU_TO_EN = dict(zip(_RU, _EN))


def tokenize(text: str):
    text = text.lower().replace("ё", "е")
    return re.findall(r"[a-zа-я0-9]+", text)


def stem(tok: str) -> str:
    """Обрезаем длинные кириллические слова для поиска."""

    if re.match(r"[а-я]", tok) and len(tok) > 6:
        return tok[:6]

    return tok


def analyze_query(q: str, fixer=None):
    """Разбирает запрос на варианты слов и исправления."""

    groups, raws, fixes = [], [], []

    for t in tokenize(q):

        if t in STOP_WORDS:
            continue

        orig = t

        # Известные исправления полных слов.
        known_correction = DISPLAY_CORRECTIONS.get(t)

        if known_correction:
            t = known_correction

        # Автоматическое исправление раскладки и опечаток.
        if fixer and t not in SYNONYMS:
            t = fixer.fix_layout(t)
            t = fixer.fix_synonym_key(t)

        base = stem(t)

        if fixer and t not in SYNONYMS:
            base = fixer.fix_typo(base)

        variants = [base]

        # Добавляем синонимы, сохраняя основной вариант.
        for s in SYNONYMS.get(t, "").split():
            if stem(s) not in variants:
                variants.append(stem(s))

        # Сохраняем известные исправления полностью.
        if t != orig:
            fixes.append((orig, t))
        elif base != stem(orig):
            fixes.append((orig, base))

        groups.append(variants)
        raws.append(t)

    joined = [
        stem(raws[i] + raws[i + 1])
        for i in range(len(raws) - 1)
    ]

    return {
        "groups": groups,
        "joined": joined,
        "fixes": fixes
    }


def normalize_query(q: str, fixer=None):
    """Возвращает плоский список токенов для поиска."""

    a = analyze_query(q, fixer)

    return [
        v
        for g in a["groups"]
        for v in g
    ] + a["joined"]


def index_tokens(text: str):
    return [stem(t) for t in tokenize(text)]


def corrected_query(query: str) -> str:
    """Исправленный запрос для отображения пользователю.

    Не показывает стемминг и не изменяет неизвестные слова.
    """

    return re.sub(
        r"[a-zа-яё0-9]+",
        lambda m: DISPLAY_CORRECTIONS.get(
            m.group().lower(),
            m.group()
        ),
        query.strip(),
        flags=re.IGNORECASE
    )