"""Kinship names, the tree layout, muchal, surnames, dates and text normalisation."""
import datetime

from django.test import TestCase
from django.utils import translation

from apps.core.dates import format_date, format_partial_date
from apps.core.muchal import muchal, next_muchal_year
from apps.core.text import normalize_apostrophes, search_key, surname_from_name
from apps.genealogy.kinship import Archive
from apps.genealogy.models import Marriage, Person

from .helpers import make_family


class KinshipTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.a = Archive(self.user)

    def rel(self, focus, other):
        return self.a.relation(self.p[focus].pk, self.p[other].pk)

    def test_direct_line(self):
        self.assertEqual(self.rel("me", "father"), "father")
        self.assertEqual(self.rel("me", "mother"), "mother")
        self.assertEqual(self.rel("me", "grandpa"), "grandfather")
        self.assertEqual(self.rel("me", "grandma"), "grandmother")
        self.assertEqual(self.rel("me", "son"), "son")
        self.assertEqual(self.rel("me", "grandson"), "grandchild")
        self.assertEqual(self.rel("grandpa", "me"), "grandchild")

    def test_siblings_by_age(self):
        self.assertEqual(self.rel("me", "older_brother"), "older_brother")    # aka
        self.assertEqual(self.rel("me", "younger_sister"), "younger_sister")  # singil
        self.assertEqual(self.rel("younger_sister", "me"), "older_brother")
        self.assertEqual(self.rel("older_brother", "me"), "younger_brother")  # uka

    def test_sibling_with_unknown_age(self):
        self.p["older_brother"].birth_year = None
        self.p["older_brother"].save()
        a = Archive(self.user)
        self.assertEqual(a.relation(self.p["me"].pk, self.p["older_brother"].pk), "brother")

    def test_aunts_uncles_and_cousins(self):
        self.assertEqual(self.rel("me", "aunt"), "paternal_aunt")                 # amma
        self.assertEqual(self.rel("me", "cousin"), "paternal_aunt_child")         # ammavachcha
        self.assertEqual(self.rel("cousin", "father"), "maternal_uncle")          # togʻa
        self.assertEqual(self.rel("cousin", "me"), "maternal_uncle_child")        # togʻavachcha
        self.assertEqual(self.rel("aunt", "me"), "nephew_niece")                  # jiyan

    def test_marriage_and_in_laws(self):
        self.assertEqual(self.rel("me", "wife"), "wife")
        self.assertEqual(self.rel("wife", "me"), "husband")
        self.assertEqual(self.rel("me", "brothers_wife"), "brothers_wife")        # yanga
        self.assertEqual(self.rel("me", "uncle_in_law"), "relative")
        self.assertEqual(self.rel("father", "wife"), "daughter_in_law")           # kelin
        self.assertEqual(self.rel("wife", "father"), "father_in_law")             # qaynota
        self.assertEqual(self.rel("wife", "mother"), "mother_in_law")             # qaynona
        self.assertEqual(self.rel("grandma", "uncle_in_law"), "son_in_law")       # kuyov
        self.assertEqual(self.rel("father", "uncle_in_law"), "sisters_husband")   # pochcha

    def test_spouse_of_grandchild(self):
        self.p["grandson_wife"] = Person.objects.create(owner=self.user, first_name="Nilufar", gender="female")
        from apps.genealogy.models import Marriage

        Marriage.objects.create(owner=self.user, husband=self.p["grandson"], wife=self.p["grandson_wife"])
        a = Archive(self.user)
        self.assertEqual(a.relation(self.p["me"].pk, self.p["grandson_wife"].pk), "granddaughter_in_law")

    def test_tree_says_you_only_for_the_viewer(self):
        from apps.genealogy.tree import build_tree

        with translation.override("uz"):
            me = self.p["me"].pk
            mine = build_tree(self.a, me, viewer_person=me)
            other = build_tree(self.a, self.p["grandpa"].pk, viewer_person=me)
            friend = build_tree(self.a, me, viewer_person=None)
        label = lambda layout, key: next(n["label"] for n in layout["nodes"] if n["id"] == self.p[key].pk)
        self.assertEqual(label(mine, "me"), "Siz")
        self.assertEqual(label(other, "grandpa"), "")
        self.assertEqual(label(other, "father"), "Oʻgʻil")
        self.assertEqual(label(friend, "me"), "")
        # Sides of the family, the direct line and the generations.
        node = lambda key: next(n for n in mine["nodes"] if n["id"] == self.p[key].pk)
        self.assertEqual((node("father")["branch"], node("mother")["branch"]), ("paternal", "maternal"))
        self.assertEqual((node("me")["branch"], node("aunt")["branch"]), ("own", "paternal"))
        self.assertTrue(node("grandpa")["direct"] and not node("aunt")["direct"])
        self.assertTrue(any(line.get("direct") for line in mine["lines"]))
        self.assertEqual([r["gen"] for r in mine["rows"]], [-2, -1, 0, 1, 2])
        with translation.override("uz"):
            maternal = build_tree(self.a, me, viewer_person=me, side="maternal")
        shown = {n["id"] for n in maternal["nodes"]}
        self.assertIn(self.p["father"].pk, shown)        # still next to the mother …
        self.assertNotIn(self.p["grandpa"].pk, shown)    # … but without his own family
        self.assertNotIn(self.p["aunt"].pk, shown)

    def test_tree_is_one_connected_chart(self):
        from collections import Counter, defaultdict

        from apps.genealogy.tree import CARD_W, COUPLE_GAP, build_tree

        # A great-uncle's branch: closed by default, shown when opened.
        great = Person.objects.create(owner=self.user, first_name="Bobokalon", gender="male")
        self.p["grandpa"].father = great
        self.p["grandpa"].save()
        uncle = Person.objects.create(owner=self.user, first_name="Qobil", gender="male", father=great)
        Person.objects.create(owner=self.user, first_name="Qobilning qizi", gender="female", father=uncle)
        a = Archive(self.user)

        compact = build_tree(a, self.p["me"].pk)
        ids = {n["id"] for n in compact["nodes"]}
        self.assertNotIn(uncle.pk, ids)
        grandpa = next(n for n in compact["nodes"] if n["id"] == self.p["grandpa"].pk)
        self.assertEqual(grandpa["sibs"], {"count": 1, "open": False, "side": "left"})
        # Parents' brothers and sisters are shown; their children (cousins)
        # are folded behind a "+N" button until unfolded.
        self.assertIn(self.p["aunt"].pk, ids)
        self.assertNotIn(self.p["cousin"].pk, ids)
        aunt = next(n for n in compact["nodes"] if n["id"] == self.p["aunt"].pk)
        self.assertEqual(aunt["kids"], {"count": 1, "open": False})
        unfolded = build_tree(a, self.p["me"].pk, unfolded={self.p["aunt"].pk})
        self.assertIn(self.p["cousin"].pk, {n["id"] for n in unfolded["nodes"]})

        opened = build_tree(a, self.p["me"].pk, opened={self.p["grandpa"].pk})
        self.assertIn(uncle.pk, {n["id"] for n in opened["nodes"]})

        everything = build_tree(a, self.p["me"].pk, open_all=True)
        full = Counter(n["id"] for n in everything["nodes"] if not n["dup"])
        self.assertEqual(set(full), set(a.people))           # everyone …
        self.assertTrue(all(v == 1 for v in full.values()))  # … exactly once
        self.assertFalse(any(n["dup"] for n in everything["nodes"]))

        # No two cards overlap, and the parents stand side by side.
        rows = defaultdict(list)
        for n in everything["nodes"]:
            rows[n["y"]].append(n["x"])
        for xs in rows.values():
            xs.sort()
            self.assertTrue(all(b - a_ >= CARD_W for a_, b in zip(xs, xs[1:])))
        pos = {n["id"]: n for n in everything["nodes"]}
        father, mother = pos[self.p["father"].pk], pos[self.p["mother"].pk]
        self.assertEqual(father["y"], mother["y"])
        self.assertAlmostEqual(mother["x"] - father["x"], CARD_W + COUPLE_GAP, delta=1)

        folded = build_tree(a, self.p["me"].pk, folded={self.p["me"].pk})
        self.assertNotIn(self.p["son"].pk, {n["id"] for n in folded["nodes"]})

    def test_labels_in_both_scripts(self):
        with translation.override("uz"):
            self.assertEqual(self.a.label(self.p["me"].pk, self.p["older_brother"].pk), "Aka")
            self.assertEqual(self.a.label(self.p["me"].pk, self.p["son"].pk), "Oʻgʻil")
            self.assertEqual(self.a.label(self.p["cousin"].pk, self.p["father"].pk), "Togʻa")
        with translation.override("uz-cyrl"):
            self.assertEqual(self.a.label(self.p["me"].pk, self.p["older_brother"].pk), "Ака")
            self.assertEqual(self.a.label(self.p["me"].pk, self.p["son"].pk), "Ўғил")
            self.assertEqual(self.a.label(self.p["cousin"].pk, self.p["father"].pk), "Тоға")
            self.assertEqual(self.a.label(self.p["me"].pk, self.p["wife"].pk), "Хотин")


class MuchalTests(TestCase):
    def test_animals(self):
        self.assertEqual(muchal(2006, 11, 19)["code"], "it")        # Dog
        self.assertEqual(muchal(1976, 8, 24)["code"], "baliq")     # Dragon ("Baliq")
        self.assertEqual(muchal(2020, 6, 1)["code"], "sichqon")    # Rat

    def test_year_changes_at_navroz(self):
        self.assertEqual(muchal(2007, 3, 20)["code"], "it")         # still the Dog year
        self.assertEqual(muchal(2007, 3, 21)["code"], "tongiz")     # Pig from Navroʻz
        self.assertFalse(muchal(2007)["certain"])
        self.assertTrue(muchal(2007, 5, 2)["certain"])

    def test_names_in_both_scripts(self):
        with translation.override("uz"):
            self.assertEqual(muchal(1976, 8, 24)["name"], "Baliq")
        with translation.override("uz-cyrl"):
            self.assertEqual(muchal(1976, 8, 24)["name"], "Балиқ")

    def test_next_muchal_year(self):
        self.assertEqual(next_muchal_year(2006, 11, 19, today=datetime.date(2026, 9, 28)), 2030)


class SurnameTests(TestCase):
    def test_suggestions(self):
        self.assertEqual(surname_from_name("Madaminjon"), "Madaminov")
        self.assertEqual(surname_from_name("Nabijon"), "Nabiyev")
        self.assertEqual(surname_from_name("Karim"), "Karimov")
        self.assertEqual(surname_from_name("Мадаминжон"), "Мадаминов")
        self.assertEqual(surname_from_name("Набижон"), "Набиев")


class DateTests(TestCase):
    def test_full_and_partial_dates(self):
        with translation.override("uz"):
            self.assertEqual(format_partial_date(2026, 9, 27), "27-sentabr 2026-yil")
            self.assertEqual(format_partial_date(2026, 9), "2026-yil sentabr")
            self.assertEqual(format_partial_date(1928), "1928-yil")
        with translation.override("uz-cyrl"):
            self.assertEqual(format_partial_date(2026, 9, 27), "2026 йил 27 сентябрь")
            self.assertEqual(format_partial_date(2026, 9), "2026 йил сентябрь")
            self.assertEqual(format_partial_date(1928), "1928 йил")
        with translation.override("ru"):
            self.assertEqual(format_partial_date(2026, 9, 27), "27 сентября 2026 г.")
            self.assertEqual(format_partial_date(2026, 9), "сентябрь 2026 г.")
            self.assertEqual(format_partial_date(1928), "1928 г.")
        with translation.override("en"):
            self.assertEqual(format_partial_date(2026, 9, 27), "September 27, 2026")
            self.assertEqual(format_partial_date(2026, 9), "September 2026")
            self.assertEqual(format_partial_date(1928), "1928")

    def test_all_months(self):
        import datetime

        with translation.override("uz"):
            months = [format_date(datetime.date(2026, m, 1)).split("-")[1].split(" ")[0] for m in range(1, 13)]
        self.assertEqual(months, ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
                                  "sentabr", "oktabr", "noyabr", "dekabr"])


class TextTests(TestCase):
    def test_apostrophes_are_normalised(self):
        for typed in ("O'g'il", "O‘g‘il", "O’g’il", "Oʻgʻil", "O`g`il"):
            self.assertEqual(normalize_apostrophes(typed), "Oʻgʻil")
        self.assertEqual(normalize_apostrophes("ma'lumot"), "maʼlumot")
        self.assertEqual(normalize_apostrophes("Ta’lim"), "Taʼlim")
        self.assertEqual(normalize_apostrophes("Alisher"), "Alisher")

    def test_search_key_is_script_independent(self):
        self.assertEqual(search_key("Alisher"), search_key("Алишер"))
        self.assertEqual(search_key("Gʻulom"), search_key("Ғулом"))
        self.assertEqual(search_key("Oʻrinboy"), search_key("Ўринбой"))
        self.assertEqual(search_key("Hasan Xo'jayev"), search_key("Ҳасан Хўжаев"))
        self.assertEqual(search_key("Jamshid Qodirov"), search_key("Джамшид Кодиров"))
        self.assertEqual(search_key("Yelena"), search_key("Елена"))
