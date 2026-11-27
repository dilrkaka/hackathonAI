"""python scripts/build_index.py data/raw/Mindbox_yml_gz.xml  -> data/processed/offers.jsonl

Необязательный флаг --only-available: оставить только доступные товары.
"""
import sys
sys.path.insert(0, ".")
from src.search.catalog import parse_catalog, save_jsonl, to_product

only_available = "--only-available" in sys.argv
xml_path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
offers = [to_product(o) for o in parse_catalog(xml_path, only_available=only_available)]
save_jsonl(offers, "data/processed/offers.jsonl")
free = sum(1 for o in offers if o["available"] and o["price"] > 0)
print(f"готово: {len(offers)} offers (из них доступных с ценой: {free})")
