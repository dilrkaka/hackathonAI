
"""Журнал запросов и отчёт об успешности поиска."""

import json
import time
from collections import Counter
from pathlib import Path


DEFAULT_LOG = "data/logs/queries.jsonl"


def log_query(record: dict, path: str = DEFAULT_LOG):
    """Сохраняет информацию об одном поисковом запросе."""
    Path(path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        **record
    }

    with open(path, "a", encoding="utf8") as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )


def read_log(path: str = DEFAULT_LOG):
    """Читает сохранённые поисковые запросы."""
    if not Path(path).exists():
        return []

    with open(path, encoding="utf8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def report(path: str = DEFAULT_LOG):
    """Формирует отчёт по качеству поисковых запросов."""
    rows = read_log(path)

    if not rows:
        return "Журнал пуст."

    # Неудачный поиск определяется по отсутствию основных совпадений.
    # Альтернативы и допродажи не считаются успешным поиском.
    zero = Counter(
        row["query"]
        for row in rows
        if row.get(
            "failed",
            row.get("n_main", 0) == 0
        )
    )

    weak = Counter(
        row["query"]
        for row in rows
        if (
            not row.get(
                "failed",
                row.get("n_main", 0) == 0
            )
            and row.get("n_main", 0) < 2
        )
    )

    typos = Counter(
        (row["query"], row["corrected"])
        for row in rows
        if row.get("fixes")
    )

    top = Counter(
        row["query"]
        for row in rows
    )

    output = [
        f"Всего запросов: {len(rows)}",
        "",
        "Ничего не нашли (добавьте синонимы / проверьте каталог):"
    ]

    output += [
        f"  {count}x  {query}"
        for query, count in zero.most_common(10)
    ] or ["  —"]

    output.append("\nМало основных совпадений (меньше 2):")

    output += [
        f"  {count}x  {query}"
        for query, count in weak.most_common(10)
    ] or ["  —"]

    output.append("\nИсправленные опечатки:")

    output += [
        f"  {count}x  {query} -> {corrected}"
        for (query, corrected), count in typos.most_common(10)
    ] or ["  —"]

    output.append("\nСамые частые запросы:")

    output += [
        f"  {count}x  {query}"
        for query, count in top.most_common(10)
    ]

    return "\n".join(output)
