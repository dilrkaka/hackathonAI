"""Нормализация запросов. Здесь живут словарь синонимов и правила разбора."""
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


def tokenize(text: str):
    text = text.lower().replace("ё", "е")
    return re.findall(r"[a-zа-я0-9]+", text)


def stem(tok: str) -> str:
    """Грубый «стеммер»: режем длинные кириллические слова до 6 символов."""
    if re.match(r"[а-я]", tok) and len(tok) > 6:
        return tok[:6]
    return tok


def normalize_query(q: str):
    toks = []
    for t in tokenize(q):
        for s in SYNONYMS.get(t, t).split():
            toks.append(s)
    # склейка соседних токенов: «max patrol» -> «maxpatrol», «крипто про» -> «криптопро»
    joined = [toks[i] + toks[i + 1] for i in range(len(toks) - 1)]
    return [stem(t) for t in toks + joined]


def index_tokens(text: str):
    return [stem(t) for t in tokenize(text)]
