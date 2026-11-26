"""Нормализация запросов. Здесь живут словарь синонимов и правила разбора.

Главное правило: синоним НЕ заменяет исходное слово, а добавляется рядом с ним.
Запрос «офис» превращается в варианты [«офис», «office»] — и находит и «Офис для дома»,
и «Microsoft Office».
"""
import re

SYNONYMS = {  # жаргон -> каноническая форма (расширять по выборке запросов!)
    "антивирь": "антивирус",
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

STOP_WORDS = {"на", "для", "и", "в", "с", "по", "от", "из", "или", "к"}  # не влияют на поиск

# раскладки клавиатуры: «ghbdtn» -> «привет»
_EN = "qwertyuiopasdfghjklzxcvbnm"
_RU = "йцукенгшщзфывапролдячсмить"
EN_TO_RU = dict(zip(_EN, _RU))
RU_TO_EN = dict(zip(_RU, _EN))


def tokenize(text: str):
    text = text.lower().replace("ё", "е")
    return re.findall(r"[a-zа-я0-9]+", text)


def stem(tok: str) -> str:
    """Грубый «стеммер»: режем длинные кириллические слова до 6 символов."""
    if re.match(r"[а-я]", tok) and len(tok) > 6:
        return tok[:6]
    return tok


def analyze_query(q: str, fixer=None):
    """Разбирает запрос.

    Возвращает словарь:
      groups — для каждого слова запроса список вариантов (слово + его синонимы);
      joined — склейки соседних слов («max patrol» -> «maxpatrol»);
      fixes  — что исправили (опечатки, раскладка): список пар (было, стало).
    """
    groups, raws, fixes = [], [], []
    for t in tokenize(q):
        if t in STOP_WORDS:
            continue
        orig = t
        if fixer and t not in SYNONYMS:
            t = fixer.fix_layout(t)
            t = fixer.fix_synonym_key(t)  # «каспрский» -> «касперский» -> kaspersky
        base = stem(t)
        if fixer and t not in SYNONYMS:
            base = fixer.fix_typo(base)
        variants = [base]
        for s in SYNONYMS.get(t, "").split():
            if stem(s) not in variants:
                variants.append(stem(s))
        if base != stem(orig):
            fixes.append((orig, base))
        groups.append(variants)
        raws.append(t)
    joined = [stem(raws[i] + raws[i + 1]) for i in range(len(raws) - 1)]
    return {"groups": groups, "joined": joined, "fixes": fixes}


def normalize_query(q: str, fixer=None):
    """Плоский список токенов для поиска (все варианты + склейки)."""
    a = analyze_query(q, fixer)
    return [v for g in a["groups"] for v in g] + a["joined"]


def index_tokens(text: str):
    return [stem(t) for t in tokenize(text)]
