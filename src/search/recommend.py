"""Допродажи: что предложить вместе с найденным товаром.

Правила простые и объяснимые: по типу найденного товара берём заготовленные запросы
(«к Windows часто берут антивирус»), ищем по ним товары и проверяем совместимость
по платформе (characteristics.is_compatible).
"""
from .characteristics import is_compatible, product_platforms
from .normalize import index_tokens, stem

# признак главного товара (слова в названии/категории) -> что предложить вместе с ним
CROSS_SELL = [
    ({"windows", "astra", "linux", "astralinux", "альт"}, ["антивирус", "резервное копирование"],
     "К операционной системе обычно берут"),
    ({"office", "офис", "microsoft365"}, ["антивирус", "резервное копирование"],
     "К офисному пакету обычно берут"),
    ({"антивирус", "kaspersky", "antivirus", "security", "dr", "web"}, ["резервное копирование", "windows"],
     "К антивирусу обычно берут"),
    ({"anydesk", "удаленный", "доступ"}, ["антивирус", "vpn"],
     "К удалённому доступу обычно берут"),
    ({"сервер", "server"}, ["антивирус для сервера", "резервное копирование"],
     "К серверу обычно берут"),
    ({"jetbrains", "pycharm", "intellij", "studio", "docker"}, ["антивирус", "резервное копирование"],
     "К инструментам разработчика обычно берут"),
]
CROSS_SELL = [({stem(w) for w in keys}, queries, why) for keys, queries, why in CROSS_SELL]
DEFAULT_QUERIES = ["антивирус", "резервное копирование"]


def pick_rules(anchor):
    toks = set(index_tokens(anchor.get("name", "") + " " + anchor.get("category_path", "")))
    for keys, queries, why in CROSS_SELL:
        if toks & keys:
            return queries, why
    return DEFAULT_QUERIES, "Часто берут вместе"


def cross_sell(engine, anchor, exclude, limit, intent=None, want_platforms=None):
    """Возвращает до `limit` товаров-допродаж из РАЗНЫХ семейств, совместимых с anchor.

    Совместимость: платформа допродажи не должна противоречить ни платформе главного
    товара, ни платформе из запроса («для windows» -> не предлагаем версию для macOS).
    Если у намерения (intent.py) есть свои допродажи — берём их, иначе правила CROSS_SELL.
    """
    if not anchor or limit <= 0:
        return []
    if intent and intent.get("upsell"):
        queries, why = intent["upsell"], intent["upsell_why"]
    else:
        queries, why = pick_rules(anchor)
    want = set(want_platforms or [])
    used, found = set(exclude), []
    for q in queries:
        for r in engine.rank_text(q, exclude=used):
            if r["family"] in used or not is_compatible(anchor, r) or r["coverage"] < 1:
                continue
            have = product_platforms(r)
            if want and have and not (have & want):
                continue  # платформа не из запроса
            used.add(r["family"])
            found.append({**r, "role": "upsell", "reason": f"{why}: {q}"})
            break
        if len(found) == limit:
            break
    return found
