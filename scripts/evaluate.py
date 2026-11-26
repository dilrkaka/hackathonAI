"""python scripts/evaluate.py  — прогон золотого набора: попал ли нужный вендор/название в топ-4."""
import sys
sys.path.insert(0, ".")
from src.search.catalog import load_jsonl
from src.search.engine import SearchEngine
from eval.golden import GOLDEN

engine = SearchEngine(load_jsonl("data/processed/offers.jsonl"))
ok = 0
for q, slug, kw in GOLDEN:
    res = engine.search(q, top_k=4)
    hit = any(r["vendor_slug"] == slug and kw.lower() in r["name"].lower() for r in res)
    ok += hit
    print(("OK  " if hit else "FAIL"), q)
    for r in res:
        print("      ", r["vendor_slug"], "|", r["name"][:80])
print(f"\nRecall@4: {ok}/{len(GOLDEN)}")
