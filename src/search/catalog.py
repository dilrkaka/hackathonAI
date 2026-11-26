"""Парсинг YML-выгрузки Softline в чистые записи.

По умолчанию в индекс идут ВСЕ товары, а флаг available сохраняется как есть.
Организаторы подтвердили: недоступные товары (цена 0) — 2-й приоритет, их показываем
только если не хватает доступных. Поэтому ранжирование (engine.py) сначала ставит
товары с ценой, а недоступные учитывает с понижающим коэффициентом.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_catalog(xml_path: str, only_available: bool = False):
    cats = {}
    offers = []
    for _, el in ET.iterparse(xml_path, events=("end",)):
        if el.tag == "category":
            cats[el.get("id")] = (el.text or "", el.get("parentId"))
        elif el.tag == "offer":
            if only_available and el.get("available") != "true":
                el.clear()
                continue
            d = {"id": el.get("id"), "group_id": el.get("group_id")}
            for c in el:
                if c.tag in ("n", "name"):
                    d["name"] = c.text or ""
                elif c.tag in ("vendor", "vendorCode", "url", "price", "oldprice", "currencyId",
                               "categoryId", "description", "picture"):
                    d[c.tag] = c.text or ""
            d["params"] = {c.get("name"): c.text for c in el if c.tag == "param"}
            m = re.match(r"https://store\.softline\.ru/([^/]+)/", d.get("url", ""))
            d["available"] = el.get("available") == "true"
            d["vendor_slug"] = m.group(1) if m else ""
            offers.append(d)
            el.clear()
    for o in offers:
        o["category_path"] = category_path(cats, o.get("categoryId"))
    return offers


def category_path(cats, cid):
    path = []
    while cid in cats:
        name, parent = cats[cid]
        path.append(name)
        cid = parent
    return " > ".join(reversed(path))


def save_jsonl(rows, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_jsonl(path):
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f]


# русские названия параметров каталога -> ключи общей схемы
PARAM_KEYS = {
    "Совместимая архитектура/платформа": "platform",
    "Тип лицензии": "license_type",
    "Срок действия": "term",
    "Язык интерфейса": "language",
    "Тип продукта": "product_type",
    "Пользователь": "user_type",
    "Тип организации": "org_type",
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0


def to_product(o):
    """Приводит запись к схеме, согласованной с командой (+ поля для поиска)."""
    params = {}
    for ru, en in PARAM_KEYS.items():
        v = o["params"].get(ru)
        if v and v != "другое или отсутствует":
            params[en] = v
    return {
        "id": o["id"],
        "group_id": o["group_id"],
        "name": o.get("name", ""),
        "vendor": o.get("vendor", ""),
        "vendor_code": o.get("vendorCode", ""),
        "description": o.get("description", ""),
        "category_id": o.get("categoryId", ""),
        "category_name": o["category_path"].split(" > ")[-1] if o["category_path"] else "",
        "price": _num(o.get("price")),
        "old_price": _num(o.get("oldprice")),
        "currency": "RUB",
        "available": bool(o.get("available", True)),
        "image_url": o.get("picture", ""),
        "url": o.get("url", ""),
        "params": params,
        # служебные поля для поиска (бэкенду не обязательны)
        "vendor_slug": o["vendor_slug"],
        "category_path": o["category_path"],
    }
