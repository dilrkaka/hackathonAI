"""python scripts/build_index.py data/raw/Mindbox_yml_gz.xml  -> data/processed/offers.jsonl"""
import sys
sys.path.insert(0, ".")
from src.search.catalog import parse_catalog, save_jsonl, to_product

offers = [to_product(o) for o in parse_catalog(sys.argv[1])]
save_jsonl(offers, "data/processed/offers.jsonl")
print(f"готово: {len(offers)} доступных offers")
