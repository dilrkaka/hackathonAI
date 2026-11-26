"""Запуск: python -m unittest discover -s tests -v   (внешних библиотек не нужно)"""
import sys
import unittest

sys.path.insert(0, ".")
from src.search.engine import SearchEngine  # noqa: E402


def offer(i, name, group=None, price=1000, available=True, vendor="", cat="Программы", params=None, desc=""):
    return {"id": str(i), "group_id": group or f"g{i}", "name": name, "vendor": vendor,
            "vendor_slug": vendor.lower(), "category_path": cat, "description": desc,
            "price": price, "available": available, "params": params or {}}


def make_engine(offers):
    return SearchEngine(offers, log_path=None)


class TestReportedBugs(unittest.TestCase):
    def test_250_in_one_group_still_gives_4_families(self):
        # ошибка №1 от проверяющего: 250 записей одной группы + 4 других товара, top_k=4
        offers = [offer(i, f"Антивирус Альфа {i}", group="big") for i in range(250)]
        offers += [offer(1000 + i, f"Антивирус Бета{i}", vendor=f"v{i}") for i in range(4)]
        res = make_engine(offers).search("антивирус", top_k=4)
        self.assertEqual(len(res), 4)
        self.assertEqual(len({r["family"] for r in res}), 4)

    def test_office_synonym_keeps_original_word(self):
        # ошибка №2: «Офис для дома» не находился по запросу «офис»
        offers = [offer(1, "Офис для дома"), offer(2, "Блокнот"), offer(3, "Microsoft Office 365")]
        names = [r["name"] for r in make_engine(offers).search("офис")]
        self.assertIn("Офис для дома", names)
        self.assertIn("Microsoft Office 365", names)


class TestQualityFeatures(unittest.TestCase):
    def setUp(self):
        self.e = make_engine([
            offer(1, "Kaspersky Small Office Security", vendor="Kaspersky", cat="Антивирусы"),
            offer(2, "Антивирус Dr.Web Security Space", vendor="Dr.Web", cat="Антивирусы"),
            offer(3, "Windows 11 Pro", vendor="Microsoft", cat="Операционные системы",
                  params={"platform": "Windows"}),
            offer(4, "Astra Linux Special Edition", vendor="Astralinux", cat="Операционные системы",
                  params={"platform": "Linux"}),
            offer(5, "Резервное копирование Кибер Бэкап", vendor="Cyberprotect", cat="Резервное копирование"),
            offer(6, "Антивирус для macOS", vendor="Mac", cat="Антивирусы", params={"platform": "macOS"}),
        ])

    def test_typo_is_fixed(self):
        out = self.e.search_full("антевирус", log=False)
        self.assertTrue(out["fixes"])
        self.assertTrue(any("нтивир" in r["name"] or "Security" in r["name"] for r in out["results"]))

    def test_wrong_keyboard_layout(self):
        out = self.e.search_full("rfcgthcrbq", log=False)  # «касперский» в английской раскладке
        self.assertEqual(out["results"][0]["name"], "Kaspersky Small Office Security")

    def test_platform_check_marks_mismatch(self):
        out = self.e.search_full("антивирус windows", log=False)
        by_name = {r["name"]: r for r in out["results"]}
        if "Антивирус для macOS" in by_name:
            self.assertEqual(by_name["Антивирус для macOS"]["checks"]["platform"], "mismatch")
            self.assertNotEqual(by_name["Антивирус для macOS"]["role"], "match")

    def test_upsell_is_compatible_and_from_other_family(self):
        out = self.e.search_full("windows 11", log=False)
        roles = [r["role"] for r in out["results"]]
        self.assertEqual(roles[0], "match")
        self.assertIn("upsell", roles)
        fams = [r["family"] for r in out["results"]]
        self.assertEqual(len(fams), len(set(fams)))
        for r in out["results"]:
            if r["role"] == "upsell":
                self.assertNotEqual(r["checks"].get("platform"), "mismatch")
                self.assertNotIn("macOS", r["name"])  # для Windows не предлагаем macOS-версию

    def test_slang_typo_and_term_in_query(self):
        out = self.e.search_full("каспрский", log=False)
        self.assertEqual(out["results"][0]["name"], "Kaspersky Small Office Security")
        out = self.e.search_full("windows на 3 года", log=False)
        self.assertEqual(out["requirements"]["term_months"], 36)
        self.assertEqual(out["results"][0]["role"], "match")  # «на 3 года» не мешает найти товар

    def test_unavailable_goes_last_but_still_shown(self):
        e = make_engine([offer(1, "Антивирус Один", price=0, available=False),
                         offer(2, "Антивирус Два", price=500)])
        res = e.search("антивирус", top_k=4)
        self.assertEqual([r["name"] for r in res], ["Антивирус Два", "Антивирус Один"])

    def test_fewer_than_four_gives_note(self):
        out = make_engine([offer(1, "Антивирус Один")]).search_full("антивирус", log=False)
        self.assertEqual(len(out["results"]), 1)
        self.assertIn("Найдено товаров: 1", out["note"])

    def test_nothing_found(self):
        out = self.e.search_full("зззззз", log=False)
        self.assertEqual(out["results"], [])


if __name__ == "__main__":
    unittest.main()
