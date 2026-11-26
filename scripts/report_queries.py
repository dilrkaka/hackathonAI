"""python scripts/report_queries.py — отчёт по журналу запросов (data/logs/queries.jsonl)."""
import sys
sys.path.insert(0, ".")
from src.search.query_log import report

print(report())
