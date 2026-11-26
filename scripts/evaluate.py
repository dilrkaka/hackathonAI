"""python scripts/evaluate.py  — прогон золотого набора: попал ли нужный вендор/название в топ-4.

Организаторы: считается совпадение продуктовой группы (семейства), оценивается топ-4.
Здесь «попадание» = в топ-4 есть товар нужного вендора с нужным словом в названии.
"""
import sys
sys.path.insert(0, ".")
from src.search.catalog import load_jsonl
from src.search.engine import SearchEngine
from eval.golden import GOLDEN

engine = SearchEngine(load_jsonl("data/processed/offers.jsonl"), log_path=None)
ok4 = ok1 = 0
for q, slug, kw in GOLDEN:
    res = engine.search(q, top_k=4)
    hits = [r["vendor_slug"] == slug and kw.lower() in r["name"].lower() for r in res]
    ok4 += any(hits)
    ok1 += bool(hits and hits[0])
    print(("OK  " if any(hits) else "FAIL"), q)
    for r in res:
        print("      ", f'{r["role"]:<11}', r["vendor_slug"], "|", r["name"][:70])
print(f"\nRecall@1: {ok1}/{len(GOLDEN)}")
print(f"Recall@4: {ok4}/{len(GOLDEN)}")
