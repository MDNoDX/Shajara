"""Kinship names, dates, text normalisation, search, PDFs and access rules."""
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from apps.accounts.models import User
from apps.core.dates import format_date, format_partial_date
from apps.core.text import normalize_apostrophes, search_key
from apps.friends.models import FriendRequest
from apps.genealogy.kinship import Archive
from apps.genealogy.models import Person

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
            mine = build_tree(self.a, self.p["me"].pk)
            other = build_tree(self.a, self.p["grandpa"].pk)
            friend = build_tree(self.a, self.p["me"].pk, viewer_is_owner=False)
        label = lambda layout, key: next(n["label"] for n in layout["nodes"] if n["id"] == self.p[key].pk)
        self.assertEqual(label(mine, "me"), "Siz")
        self.assertEqual(label(other, "grandpa"), "")
        self.assertEqual(label(other, "father"), "Oʻgʻil")
        self.assertEqual(label(friend, "me"), "")

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
        # Parents' brothers and sisters are open by default (the aunt's family).
        self.assertIn(self.p["cousin"].pk, ids)

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


class SearchAndStorageTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_cyrillic_query_finds_latin_name_and_back(self):
        Person.objects.create(owner=self.user, first_name="Олим", last_name="Содиқов", gender="male")
        html = self.client.get(reverse("genealogy:search"), {"q": "Лайло"}).content.decode()
        self.assertIn("Laylo Nurmatova", html)
        html = self.client.get(reverse("genealogy:search"), {"q": "olim sodiqov"}).content.decode()
        self.assertIn("Олим Содиқов", html)

    def test_names_are_stored_as_typed(self):
        self.client.post(reverse("genealogy:person_create"), {
            "first_name": "Гулчеҳра", "last_name": "Ra'noyeva", "gender": "female",
        })
        person = Person.objects.get(first_name="Гулчеҳра")
        self.assertEqual(person.last_name, "Raʼnoyeva")  # apostrophe normalised, letters untouched


class FormValidationTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def post_relative(self, **data):
        base = {"relation": "child", "first_name": "Yangi", "gender": "male"}
        base.update(data)
        return self.client.post(reverse("genealogy:relative_add", args=[self.p["me"].pk]), base)

    def test_add_child_with_other_parent(self):
        response = self.post_relative(other_parent=self.p["wife"].pk)
        self.assertEqual(response.status_code, 302)
        child = Person.objects.get(first_name="Yangi")
        self.assertEqual((child.father, child.mother), (self.p["me"], self.p["wife"]))

    def test_cannot_add_second_father(self):
        response = self.post_relative(relation="father")
        self.assertContains(response, "Bu odamning otasi shajarada allaqachon bor.")

    def test_cycle_is_rejected(self):
        response = self.post_relative(relation="child", existing=self.p["grandpa"].pk, first_name="")
        self.assertContains(response, "odam oʻzining ajdodiga aylanib qoladi")

    def test_future_date_and_invalid_day(self):
        response = self.client.post(reverse("genealogy:person_create"), {
            "first_name": "Sinov", "gender": "male", "birth_year": "2999",
        })
        self.assertContains(response, "Qiymat eng koʻpi")
        response = self.client.post(reverse("genealogy:person_create"), {
            "first_name": "Sinov", "gender": "male", "birth_year": "2001", "birth_month": "2", "birth_day": "29",
        })
        self.assertContains(response, "Tanlangan oyda bunday kun yoʻq.")


class PdfTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family(cyrillic=True)
        self.client.force_login(self.user)

    def assert_pdf(self, response, filename):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(b"DejaVuSans", response.content)  # Unicode font embedded
        self.assertIn(filename, response["Content-Disposition"])

    def test_pdfs_follow_language(self):
        # User prefers Cyrillic: file names are Cyrillic too (RFC 5987 encoded).
        self.assert_pdf(self.client.get(reverse("genealogy:tree_pdf_for", args=[self.user.username])),
                        "%D1%88%D0%B0%D0%B6%D0%B0%D1%80%D0%B0.pdf")  # шажара.pdf
        self.assert_pdf(self.client.get(reverse("genealogy:family_book")), "%D1%88%D0%B0%D0%B6%D0%B0%D1%80%D0%B0")
        self.assert_pdf(self.client.get(reverse("genealogy:person_pdf", args=[self.p["grandpa"].pk])), ".pdf")
        self.user.preferred_language = "uz"
        self.user.save()
        self.assert_pdf(self.client.get(reverse("genealogy:tree_pdf_for", args=[self.user.username])), "shajara.pdf")


class AccessTests(TestCase):
    def setUp(self):
        self.owner, self.p = make_family()
        self.other = User.objects.create_user("begona", "b@example.com", "x-parol-12345", preferred_language="uz-cyrl")
        self.client.force_login(self.other)

    def test_strangers_cannot_view(self):
        response = self.client.get(reverse("genealogy:person", args=[self.p["me"].pk]))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Кириш тақиқланган.", status_code=403)

    def test_friends_can_view_but_not_edit(self):
        FriendRequest.objects.create(from_user=self.other, to_user=self.owner, status=FriendRequest.Status.ACCEPTED)
        self.assertEqual(self.client.get(reverse("genealogy:person", args=[self.p["me"].pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("genealogy:tree_for", args=[self.owner.username])).status_code, 200)
        response = self.client.get(reverse("genealogy:person_edit", args=[self.p["me"].pk]))
        self.assertContains(response, "Ушбу маълумотни ўзгартириш ҳуқуқингиз йўқ.", status_code=403)

    def test_friend_request_flow(self):
        self.client.post(reverse("friends:send", args=[self.owner.pk]))
        req = FriendRequest.objects.get(from_user=self.other, to_user=self.owner)
        self.client.force_login(self.owner)
        home = self.client.get(reverse("home")).content.decode()
        self.assertIn('class="badge"', home)
        self.client.post(reverse("friends:answer", args=[req.pk]), {"answer": "accept"})
        req.refresh_from_db()
        self.assertEqual(req.status, FriendRequest.Status.ACCEPTED)
