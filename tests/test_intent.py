"""Тесты намерения, приоритета категорий, допродаж и «минимум 4 товара».

Запуск: python -m unittest discover -s tests -v   (внешних библиотек не нужно)
"""
import sys
import unittest

sys.path.insert(0, ".")
from src.search.engine import SearchEngine  # noqa: E402
from src.search.intent import detect_intent  # noqa: E402


def offer(i, name, cat="Программы", vendor="", params=None, price=1000, desc="", available=True):
    return {"id": str(i), "group_id": f"g{i}", "name": name, "vendor": vendor,
            "vendor_slug": vendor.lower(), "category_path": cat, "description": desc,
            "price": price, "available": available, "params": params or {}}


CATALOG = [
    offer(1, "Windows Server 2022 Standard", "Серверное ПО", "Microsoft", {"platform": "Windows"}),
    offer(2, "Astra Linux Server Edition", "Серверное ПО", "Astralinux", {"platform": "Linux"}),
    offer(3, "VMware vSphere виртуализация серверов", "Виртуализация", "VMware"),
    offer(4, "Kaspersky Endpoint Security для сервера", "Антивирусы", "Kaspersky", {"platform": "Windows"}),
    offer(5, "Kaspersky Standard", "Антивирусы", "Kaspersky", {"platform": "Windows"}),
    offer(6, "Dr.Web Security Space", "Антивирусы", "Dr.Web", {"platform": "Windows"}),
    offer(7, "ESET NOD32 Antivirus", "Антивирусы", "ESET", {"platform": "Windows"}),
    offer(8, "Антивирус для macOS", "Антивирусы", "Mac", {"platform": "macOS"}),
    offer(9, "Кибер Бэкап Стандарт", "Резервное копирование", "Cyberprotect", {"platform": "Windows"}),
    offer(10, "JetBrains PyCharm Professional", "Среды разработки", "JetBrains"),
    offer(11, "Visual Studio Professional", "Среды разработки", "Microsoft", {"platform": "Windows"}),
    offer(12, "Docker Business", "Инструменты разработчика", "Docker"),
    offer(13, "Блокнот Плюс", "Офисные программы", "Noname"),
    offer(14, "Игра Сервер Мечты", "Игры", "Games", desc="сервер сервер сервер"),
    offer(15, "Microsoft Office для дома", "Офисные программы", "Microsoft", {"platform": "Windows"}),
]


def engine(offers=None):
    return SearchEngine(offers or CATALOG, log_path=None)


class TestIntentDetection(unittest.TestCase):
    def test_three_hackathon_queries(self):
        self.assertEqual(detect_intent("сервер")["name"], "server")
        self.assertEqual(detect_intent("ноут для программиста")["name"], "dev_laptop")
        self.assertEqual(detect_intent("защита компьютера от вирусов")["name"], "antivirus")

    def test_plain_product_query_has_no_intent(self):
        self.assertIsNone(detect_intent("microsoft office для дома"))
        self.assertIsNone(detect_intent("anydesk"))

    def test_consumed_words(self):
        self.assertEqual(detect_intent("ноут для программиста")["consumed"], {"ноут", "программиста"})


class TestHackathonQueries(unittest.TestCase):
    def setUp(self):
        self.e = engine()

    def test_server_query(self):
        out = self.e.search_full("сервер", log=False)
        self.assertEqual(out["intent"]["name"], "server")
        top = out["results"][0]
        self.assertEqual(top["role"], "match")
        self.assertTrue("сервер" in (top["name"] + top["category_path"]).lower()
                        or "server" in top["name"].lower())

    def test_category_priority_beats_keyword_spam(self):
        # у игры слово «сервер» в описании 3 раза, но категория не та -> она не должна быть первой
        out = self.e.search_full("сервер", log=False)
        self.assertNotEqual(out["results"][0]["name"], "Игра Сервер Мечты")

    def test_dev_laptop_query(self):
        out = self.e.search_full("ноут для программиста", log=False)
        matches = [r["name"] for r in out["results"] if r["role"] == "match"]
        self.assertTrue(matches)
        self.assertTrue(any(w in " ".join(matches) for w in ("PyCharm", "Visual Studio", "Docker")))
        self.assertNotIn("Блокнот Плюс", matches)

    def test_antivirus_query(self):
        out = self.e.search_full("защита компьютера от вирусов", log=False)
        matches = [r for r in out["results"] if r["role"] == "match"]
        self.assertGreaterEqual(len(matches), 3)
        for r in matches:
            self.assertIn("Антивирусы", r["category_path"])

    def test_server_antivirus_not_first_for_desktop_query(self):
        # «защита компьютера» — не про сервер: антивирус «для сервера» не должен быть первым
        out = self.e.search_full("защита компьютера от вирусов", log=False)
        self.assertNotIn("сервера", out["results"][0]["name"])

    def test_corrected_is_readable(self):
        out = self.e.search_full("ноут для программиста", log=False)
        self.assertEqual(out["corrected"], "ноут для программиста")


class TestUpsellAndCompatibility(unittest.TestCase):
    def test_server_gets_upsell(self):
        out = engine().search_full("сервер", log=False)
        roles = [r["role"] for r in out["results"]]
        self.assertIn("upsell", roles)

    def test_upsell_for_windows_query_is_not_macos(self):
        out = engine().search_full("защита компьютера от вирусов windows", log=False)
        for r in out["results"]:
            if r["role"] == "upsell":
                self.assertNotIn("macOS", r["name"])
                self.assertNotEqual(r["checks"].get("platform"), "mismatch")

    def test_upsell_has_reason_and_other_family(self):
        out = engine().search_full("защита компьютера от вирусов", log=False)
        fams = [r["family"] for r in out["results"]]
        self.assertEqual(len(fams), len(set(fams)))
        for r in out["results"]:
            if r["role"] == "upsell":
                self.assertTrue(r["reason"])


class TestMinFourProducts(unittest.TestCase):
    QUERIES = ["сервер", "ноут для программиста", "защита компьютера от вирусов",
               "антивирус", "windows", "бэкап", "офис", "зззззз", "pycharm"]

    def test_always_four_when_catalog_is_big_enough(self):
        e = engine()
        for q in self.QUERIES:
            res = e.search(q, top_k=4)
            if q == "зззззз":
                self.assertEqual(res, [], "Мусорный запрос не должен получать нерелевантные результаты")
                out = e.search_full(q, log=False)
                self.assertIn("ничего не найдено", out["note"].lower())
                self.assertTrue(all(r["role"] == "popular" for r in out["popular_recommendations"]))
            else:
                self.assertEqual(len(res), 4, q)
                self.assertEqual(len({r["family"] for r in res}), 4, q)

    def test_top_k_below_four_is_raised_to_four(self):
        self.assertEqual(len(engine().search("антивирус", top_k=2)), 4)

    def test_filler_skips_wrong_platform(self):
        out = engine().search_full("pycharm windows", log=False)
        for r in out["results"]:
            self.assertNotEqual(r["checks"].get("platform"), "mismatch")

    def test_small_catalog_gives_honest_note(self):
        out = engine(CATALOG[:2]).search_full("сервер", log=False)
        self.assertEqual(len(out["results"]), 2)
        self.assertIn("Найдено товаров: 2", out["note"])


if __name__ == "__main__":
    unittest.main()
