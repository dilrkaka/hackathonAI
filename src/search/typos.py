"""Исправление опечаток по словарю каталога (без внешних библиотек, только difflib)."""
import difflib
from collections import defaultdict

from .normalize import EN_TO_RU, RU_TO_EN, SYNONYMS, stem


class SpellFixer:
    def __init__(self, df):
        """df — словарь {слово индекса: в скольких товарах встречается}."""
        self.df = df
        self.by_len = defaultdict(list)
        for w in df:
            self.by_len[len(w)].append(w)

    def fix_typo(self, tok: str) -> str:
        """Слово есть в каталоге — не трогаем. Нет — ищем самое похожее."""
        if tok in self.df or len(tok) < 5 or any(c.isdigit() for c in tok):
            return tok
        cands = []
        for n in (len(tok) - 1, len(tok), len(tok) + 1):
            cands += self.by_len.get(n, [])
        best = difflib.get_close_matches(tok, cands, n=5, cutoff=0.8)
        if not best:
            return tok
        # из похожих берём самое похожее, при равенстве — самое частое
        return max(best, key=lambda w: (round(difflib.SequenceMatcher(None, tok, w).ratio(), 2), self.df[w]))

    def fix_synonym_key(self, tok: str) -> str:
        """Опечатка в слове из словаря синонимов («каспрский»), которого нет в каталоге."""
        if tok in SYNONYMS or stem(tok) in self.df or len(tok) < 5:
            return tok
        best = difflib.get_close_matches(tok, list(SYNONYMS), n=1, cutoff=0.85)
        return best[0] if best else tok

    def fix_layout(self, tok: str) -> str:
        """«rfcgthcrbq» (набрали в английской раскладке) -> «касперский»."""
        if stem(tok) in self.df or tok in SYNONYMS or tok.isdigit():
            return tok
        table = EN_TO_RU if tok[0] in EN_TO_RU else RU_TO_EN
        if not all(c in table for c in tok):
            return tok
        conv = "".join(table[c] for c in tok)
        if stem(conv) in self.df or conv in SYNONYMS:
            return conv
        return tok
