
"""Определение намерения пользователя и приоритетов категорий."""

from .normalize import tokenize


INTENTS = [
    {
        "name": "antivirus",
        "label": "Защита от вирусов",
        "rules": [
            [("вирус", "антивир", "вредонос", "зловред", "троян",
              "malware", "virus", "шпионск")],
            [
                ("защит", "безопасн"),
                ("компьют", "комп", "пк", "ноут", "windows", "сервер", "рабоч")
            ],
        ],
        "expand": ["антивирус", "защита", "security", "kaspersky", "dr.web"],
        "terms": [
            "антивир", "antivir", "защит", "безопасн", "security",
            "kaspersky", "касперск", "eset", "endpoint"
        ],
        "upsell": ["резервное копирование", "vpn"],
        "upsell_why": "К защите от вирусов часто берут",
    },
    {
        "name": "server",
        "label": "Серверы и серверное ПО",
        "rules": [[("сервер", "server", "серверн")]],
        "expand": ["server", "сервер", "виртуализация"],
        "terms": [
            "сервер", "server", "виртуал", "vmware", "hyper", "proxmox"
        ],
        "upsell": ["антивирус для сервера", "резервное копирование"],
        "upsell_why": "К серверу обычно берут",
    },
    {
        "name": "dev_laptop",
        "label": "Рабочее место программиста",
        "rules": [
            [("программист", "разработчик", "разработк",
              "developer", "кодер", "девелопер")],
            [
                ("ноут", "laptop", "комп", "пк"),
                ("программ", "разраб", "dev", "код")
            ],
            [
                ("рабоч"),
                ("мест"),
                ("программист", "разработчик", "разработк",
                 "developer", "кодер", "девелопер")
            ],
        ],
        "expand": [
            "ноутбук", "laptop", "lenovo", "hp", "asus",
            "acer", "dell", "msi", "macbook",
            "jetbrains", "pycharm", "intellij",
            "visual studio", "docker", "gitlab", "github"
        ],
        "laptop_terms": [
            "ноутбук", "laptop", "macbook", "thinkpad"
        ],
        "software_terms": [
            "jetbrains", "pycharm", "intellij",
            "visualstudio", "docker", "gitlab", "github"
        ],
        "terms": [
            "ноутбук", "laptop", "macbook", "thinkpad",
            "jetbrains", "pycharm", "intellij",
            "visualstudio", "docker", "gitlab", "github"
        ],
        "upsell": ["антивирус", "резервное копирование", "vpn"],
        "upsell_why": "Для рабочего места программиста часто берут",
    },
]


ACCESSORY_TERMS = (
    "сумк", "чехол", "аксессуар", "рюкзак",
    "backpack", "bag", "sleeve", "case",
    "адаптер", "adapter", "заряд", "charger",
    "кабел", "cable", "мыш", "mouse",
    "клавиатур", "keyboard", "подставк",
    "док-станц", "dock"
)


def _starts(tok, prefixes):
    return any(tok.startswith(prefix) for prefix in prefixes)


def detect_intent(query: str):
    """Определяет намерение пользователя."""
    tokens = tokenize(query)

    for intent in INTENTS:
        for rule in intent["rules"]:
            if all(
                any(_starts(token, group) for token in tokens)
                for group in rule
            ):
                all_prefixes = [
                    prefix
                    for current_rule in intent["rules"]
                    for group in current_rule
                    for prefix in group
                ]

                consumed = {
                    token
                    for token in tokens
                    if _starts(token, all_prefixes)
                }

                result = {
                    **intent,
                    "consumed": consumed
                }

                if intent["name"] == "dev_laptop":
                    has_laptop = any(
                        _starts(token, ("ноут", "laptop"))
                        for token in tokens
                    )

                    result["mode"] = (
                        "laptop" if has_laptop else "balanced"
                    )

                return result

    return None


def strip_consumed(text: str, intent) -> str:
    """Убирает слова, уже объяснённые намерением."""
    if not intent:
        return text

    return " ".join(
        token
        for token in tokenize(text)
        if token not in intent["consumed"]
    )


def _is_physical_laptop(offer, intent):
    """Проверяет, что товар является ноутбуком, а не аксессуаром."""
    name = offer.get("name", "").lower()
    category = offer.get("category_path", "").lower()
    combined = " ".join([name, category])

    if any(term in combined for term in ACCESSORY_TERMS):
        return False

    name_tokens = tokenize(name)

    if any(
        _starts(token, intent["laptop_terms"])
        for token in name_tokens
    ):
        return True

    category_parts = (
        category
        .replace("/", ">")
        .replace("|", ">")
        .split(">")
    )

    for part in category_parts:
        part_tokens = tokenize(part.strip())

        if (
            part_tokens
            and any(
                _starts(token, ("ноутбук", "laptop"))
                for token in part_tokens
            )
        ):
            return True

    return False


def _is_development_software(offer, intent):
    """Проверяет, что товар действительно относится к ПО разработки."""
    name = offer.get("name", "").lower()
    category = offer.get("category_path", "").lower()
    vendor = offer.get("vendor", "").lower()

    # Отрицательный контекст: товар явно поставляется без Docker.
    if "w/o docker" in name or "without docker" in name:
        return False

    # Visual Studio проверяется как цельное название,
    # а не по отдельному слову Visual.
    if "visual studio" in name:
        return True

    if "pycharm" in name or "intellij" in name:
        return True

    if "docker" in name:
        return (
            "инструменты разработчика" in category
            or "разработка" in category
            or "docker" in vendor
            or "docker business" in name
        )

    if any(
        term in name
        for term in ("gitlab", "github")
    ):
        return True

    # JetBrains — название разработчика программ.
    if "jetbrains" in vendor or "jetbrains" in name:
        return True

    return False


def intent_match_type(offer, intent):
    """Определяет, к какой группе относится товар."""
    if not intent:
        return None

    name = offer.get("name", "")
    category = offer.get("category_path", "")
    vendor = offer.get("vendor", "")

    if intent["name"] == "dev_laptop":
        if _is_physical_laptop(offer, intent):
            return "laptop"

        if _is_development_software(offer, intent):
            return "software"

        return None

    text = " ".join([name, category, vendor])
    tokens = tokenize(text)

    if any(
        _starts(token, intent["terms"])
        for token in tokens
    ):
        return "match"

    return None


def intent_hit(offer, intent) -> bool:
    """Проверяет соответствие товара намерению."""
    return intent_match_type(offer, intent) is not None
