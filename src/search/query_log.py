"""Журнал запросов + отчёт о неудачных поисках (бонус по ТЗ: аналитика поиска)."""
import json
import time
from collections import Counter
from pathlib import Path

DEFAULT_LOG = "data/logs/queries.jsonl"


def log_query(record: dict, path: str = DEFAULT_LOG):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    record = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), **record}
    with open(path, "a", encoding="utf8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_log(path: str = DEFAULT_LOG):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f if line.strip()]


def report(path: str = DEFAULT_LOG):
    """Текстовый отчёт: какие запросы не нашли ничего, где мало точных совпадений, что часто исправляем."""
    rows = read_log(path)
    if not rows:
        return "Журнал пуст."
    zero = Counter(r["query"] for r in rows if r["n_results"] == 0)
    weak = Counter(r["query"] for r in rows if r["n_results"] > 0 and r["n_main"] < 2)
    typos = Counter((r["query"], r["corrected"]) for r in rows if r.get("fixes"))
    top = Counter(r["query"] for r in rows)
    out = [f"Всего запросов: {len(rows)}", ""]
    out.append("Ничего не нашли (добавьте синонимы / проверьте каталог):")
    out += [f"  {n}x  {q}" for q, n in zero.most_common(10)] or ["  —"]
    out.append("\nМало точных совпадений (меньше 2):")
    out += [f"  {n}x  {q}" for q, n in weak.most_common(10)] or ["  —"]
    out.append("\nИсправленные опечатки:")
    out += [f"  {n}x  {q} -> {c}" for (q, c), n in typos.most_common(10)] or ["  —"]
    out.append("\nСамые частые запросы:")
    out += [f"  {n}x  {q}" for q, n in top.most_common(10)]
    return "\n".join(out)
