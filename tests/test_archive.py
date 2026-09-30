"""History and undo, duplicates, the album, GEDCOM import, two-step sign-in,
push subscriptions, the weekly backup and the new tree views."""
import datetime
import json
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts import totp
from apps.accounts.models import Membership
from apps.genealogy import duplicates, gedcom, history
from apps.genealogy.kinship import Archive
from apps.genealogy.models import Change, Marriage, Media, Person
from apps.notify import service
from apps.notify.models import BotState, NotificationSettings, PushSubscription

from .helpers import PASSWORD, make_family


def png(size=(60, 40), colour="#27357e"):
    buf = BytesIO()
    Image.new("RGB", size, colour).save(buf, "PNG")
    return SimpleUploadedFile("rasm.png", buf.getvalue(), content_type="image/png")


class HistoryTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_edit_is_logged_and_undone(self):
        person = self.p["aunt"]
        self.client.post(reverse("genealogy:person_edit", args=[person.pk]), {
            "first_name": "Dilnoza", "last_name": "Yangi", "gender": "female", "birth_year": "1961",
            "father": person.father_id, "mother": person.mother_id})
        person.refresh_from_db()
        self.assertEqual((person.last_name, person.birth_year), ("Yangi", 1961))
        change = Change.objects.get(person=person, action="updated")
        self.assertEqual(set(change.details["fields"]), {"last_name", "birth_year"})
        self.assertEqual(change.details["fields"]["last_name"], ["Aliyeva", "Yangi"])
        page = self.client.get(reverse("genealogy:history")).content.decode()
        self.assertIn("Dilnoza Yangi", page)
        self.client.post(reverse("genealogy:history_undo", args=[change.pk]))
        person.refresh_from_db()
        self.assertEqual((person.last_name, person.birth_year), ("Aliyeva", 1960))
        change.refresh_from_db()
        self.assertFalse(change.can_undo)

    def test_delete_is_restored_with_links(self):
        aunt, cousin = self.p["aunt"], self.p["cousin"]
        husband = self.p["uncle_in_law"]
        pk = aunt.pk
        self.client.post(reverse("genealogy:person_delete", args=[pk]))
        self.assertFalse(Person.objects.filter(pk=pk).exists())
        cousin.refresh_from_db()
        self.assertIsNone(cousin.mother)
        change = Change.objects.get(action="deleted")
        self.client.post(reverse("genealogy:history_undo", args=[change.pk]))
        restored = Person.objects.get(pk=pk)                      # the same address works again
        cousin.refresh_from_db()
        self.assertEqual(cousin.mother, restored)
        self.assertEqual(restored.father, self.p["grandpa"])
        self.assertTrue(Marriage.objects.filter(husband=husband, wife=restored).exists())

    def test_viewers_cannot_undo(self):
        other, _p = make_family(username="mehmon")
        Membership.objects.create(owner=self.user, member=other, role="viewer")
        change = history.record(self.user, self.user, Change.Action.UPDATED, self.p["aunt"],
                                details={"fields": {"last_name": ["Eski", "Aliyeva"]}}, before={"last_name": "Eski"})
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse("genealogy:history_undo", args=[change.pk])).status_code, 403)


class DuplicateTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_adding_a_likely_duplicate_asks_first(self):
        data = {"first_name": "Дилноза", "last_name": "Алиева", "gender": "female"}  # the aunt, in Cyrillic
        response = self.client.post(reverse("genealogy:person_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dilnoza Aliyeva")
        self.assertEqual(Person.objects.filter(owner=self.user, gender="female", birth_year=None).count(), 0)
        response = self.client.post(reverse("genealogy:person_create"), {**data, "confirm_duplicate": "on"})
        self.assertEqual(response.status_code, 302)

    def test_merge_keeps_everything(self):
        aunt = self.p["aunt"]
        twin = Person.objects.create(owner=self.user, first_name="Dilnoza", last_name="Aliyeva", gender="female",
                                     birth_place="Andijon", occupation="Shifokor")
        child = Person.objects.create(owner=self.user, first_name="Bola", gender="male", mother=twin)
        self.assertEqual(duplicates.pairs(self.user), [(aunt, twin)])
        page = self.client.get(reverse("genealogy:duplicates"))
        self.assertContains(page, "Dilnoza Aliyeva")
        self.client.post(reverse("genealogy:merge"), {"keep": aunt.pk, "drop": twin.pk})
        aunt.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual((aunt.birth_place, aunt.occupation, aunt.birth_year), ("Andijon", "Shifokor", 1960))
        self.assertEqual(child.mother, aunt)
        self.assertFalse(Person.objects.filter(pk=twin.pk).exists())
        self.assertEqual(duplicates.pairs(self.user), [])


class AlbumTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_upload_shrinks_and_is_private(self):
        person = self.p["grandpa"]
        big = png((3000, 1500))
        note = SimpleUploadedFile("xat.txt", b"salom", content_type="text/plain")
        self.client.post(reverse("genealogy:media_upload", args=[person.pk]),
                         {"files": [big, note], "caption": "Toʻy kuni", "year": "1955"})
        item = Media.objects.get(person=person)                 # the text file is refused
        self.assertEqual((item.kind, item.caption, item.year), ("photo", "Toʻy kuni", 1955))
        served = self.client.get(item.file.url)
        self.assertEqual(served.status_code, 200)
        self.assertLessEqual(max(Image.open(BytesIO(served.content)).size), 1800)
        page = self.client.get(person.get_absolute_url()).content.decode()
        self.assertIn(item.file.url, page)
        # Use it as the main photo; then delete it.
        self.client.post(reverse("genealogy:media_portrait", args=[item.pk]))
        person.refresh_from_db()
        self.assertEqual(person.photo.name, item.file.name)
        self.client.logout()
        self.assertEqual(self.client.get(item.file.url).status_code, 404)
        self.client.force_login(self.user)
        self.client.post(reverse("genealogy:media_delete", args=[item.pk]))
        person.refresh_from_db()
        self.assertFalse(person.photo)
        self.assertFalse(Media.objects.exists())

    def test_photos_appear_in_the_pdfs(self):
        person = self.p["me"]
        self.client.post(reverse("genealogy:person_edit", args=[person.pk]), {
            "first_name": person.first_name, "gender": "male", "birth_year": "1984", "photo": png()})
        book = self.client.get(reverse("genealogy:family_book"))
        self.assertTrue(book.content.startswith(b"%PDF"))
        self.assertIn(b"/Image", book.content)
        poster = self.client.get(reverse("genealogy:tree_pdf_for", args=[self.user.username]) + "?size=A2&all=1")
        self.assertTrue(poster.content.startswith(b"%PDF"))
        self.assertIn(b"/Image", poster.content)
        self.assertIn("A2", poster["Content-Disposition"])


class GedcomImportTests(TestCase):
    def test_round_trip(self):
        user, p = make_family()
        text = gedcom.export(Archive(user), "Timur")
        other, _p = make_family(username="yangi")
        Person.objects.filter(owner=other).exclude(pk=other.person_id).delete()
        counts = gedcom.import_file(other, text.encode("utf-8"))
        self.assertEqual(counts["people"], len(p))
        imported = Archive(other)
        me = next(x for x in imported.people.values() if x.first_name == "Timur" and x.pk != other.person_id)
        self.assertEqual((me.birth_year, me.birth_month, me.birth_day), (1984, 9, 27))
        self.assertEqual(imported.people[me.father_id].first_name, "Rustam")
        self.assertEqual(imported.label(me.pk, me.father_id), "Ota")
        self.assertEqual(len(imported.spouses(me.pk)), 1)
        grandpa = next(x for x in imported.people.values() if x.first_name == "Karim")
        self.assertTrue(grandpa.is_deceased)
        self.assertEqual(grandpa.death_year, 2001)

    def test_dates_and_upload(self):
        self.assertEqual(gedcom.parse_date("ABT 12 MAR 1950"), (1950, 3, 12))
        self.assertEqual(gedcom.parse_date("BET 1901 AND 1905"), (1901, None, None))
        self.assertEqual(gedcom.parse_date("JUL 1977"), (1977, 7, None))
        self.assertEqual(gedcom.parse_date("nonsense"), (None, None, None))
        user, _p = make_family()
        self.client.force_login(user)
        bad = SimpleUploadedFile("x.ged", b"this is not gedcom", content_type="text/plain")
        response = self.client.post(reverse("genealogy:gedcom_import"), {"file": bad}, follow=True)
        self.assertContains(response, "GEDCOM")
        good = SimpleUploadedFile("oila.ged", ("0 HEAD\n1 CHAR UTF-8\n0 @I1@ INDI\n1 NAME Alisher /Navoiy/\n1 SEX M\n"
                                               "1 BIRT\n2 DATE 9 FEB 1441\n2 PLAC Hirot\n0 TRLR\n").encode(),
                                  content_type="text/plain")
        self.client.post(reverse("genealogy:gedcom_import"), {"file": good})
        navoiy = Person.objects.get(owner=user, first_name="Alisher")
        self.assertEqual((navoiy.last_name, navoiy.birth_year, navoiy.birth_place), ("Navoiy", 1441, "Hirot"))


class TwoFactorTests(TestCase):
    def test_setup_and_sign_in(self):
        user, _p = make_family()
        self.client.force_login(user)
        self.client.get(reverse("accounts:two_factor_setup"))
        secret = self.client.session["totp_new"]
        wrong = self.client.post(reverse("accounts:two_factor_setup"), {"code": "000000"})
        self.assertEqual(wrong.status_code, 200)
        page = self.client.post(reverse("accounts:two_factor_setup"), {"code": totp.code_at(secret, int(__import__("time").time() // 30))})
        user.refresh_from_db()
        self.assertTrue(user.totp_enabled)
        self.assertEqual(len(user.recovery_codes), 8)
        recovery = page.context["codes"][0]

        # The password alone is no longer enough.
        self.client.logout()
        response = self.client.post(reverse("accounts:login"), {"username": user.username, "password": PASSWORD})
        self.assertRedirects(response, reverse("accounts:two_factor"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("home")).context.get("people_count"), None)  # still a guest
        self.client.post(reverse("accounts:two_factor"), {"code": "123456"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.post(reverse("accounts:two_factor"), {"code": recovery})       # a recovery code works once
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        user.refresh_from_db()
        self.assertEqual(len(user.recovery_codes), 7)

    def test_codes(self):
        secret = "JBSWY3DPEHPK3PXP"
        self.assertEqual(totp.code_at(secret, 1), "996554")     # RFC 4226-style reference value
        self.assertTrue(totp.verify(secret, totp.code_at(secret, 50), now=50 * 30 + 5))
        self.assertTrue(totp.verify(secret, totp.code_at(secret, 49), now=50 * 30 + 5))   # clock drift
        self.assertFalse(totp.verify(secret, totp.code_at(secret, 40), now=50 * 30 + 5))


class PushAndBackupTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_subscribe_and_unsubscribe(self):
        sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "k" * 80, "auth": "a" * 20}}
        ok = self.client.post(reverse("notify:push_subscribe"), json.dumps(sub), content_type="application/json")
        self.assertTrue(ok.json()["ok"])
        self.assertEqual(PushSubscription.objects.get().user, self.user)
        bad = self.client.post(reverse("notify:push_subscribe"), "{}", content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        self.client.post(reverse("notify:push_unsubscribe"), json.dumps({"endpoint": sub["endpoint"]}),
                         content_type="application/json")
        self.assertFalse(PushSubscription.objects.exists())

    @override_settings(VAPID_PUBLIC_KEY="pub", VAPID_PRIVATE_KEY="priv")
    def test_due_reminders_are_pushed_once(self):
        PushSubscription.objects.create(user=self.user, endpoint="https://push.example/1", p256dh="k", auth="a")
        service.generate(self.user, datetime.date(2026, 9, 27))
        nine = datetime.datetime(2026, 9, 27, 4, 0, tzinfo=datetime.timezone.utc)
        with mock.patch("apps.notify.push.send", return_value=True) as send:
            self.assertEqual(service.send_pending_push(now=nine), 1)
            self.assertEqual(service.send_pending_push(now=nine), 0)
        payload = send.call_args.args[1]
        self.assertIn("Timur Nurmatov", payload["title"])
        self.assertTrue(payload["url"].startswith("/"))

    @override_settings(TELEGRAM_BOT_TOKEN="123:abc")
    def test_weekly_backup_goes_to_the_admin_once_a_week(self):
        prefs = NotificationSettings.for_user(self.user)
        prefs.telegram_chat_id, prefs.backup_telegram = 555, True
        prefs.save()
        monday = datetime.datetime(2026, 9, 28, 3, 0, tzinfo=datetime.timezone.utc)
        with mock.patch("apps.notify.telegram.send_document") as send:
            self.assertEqual(service.weekly_backup(now=monday), 0)       # not an administrator
            self.user.is_superuser = True
            self.user.save()
            self.assertEqual(service.weekly_backup(now=monday), 1)
            self.assertEqual(service.weekly_backup(now=monday + datetime.timedelta(days=2)), 0)
            self.assertEqual(service.weekly_backup(now=monday + datetime.timedelta(days=7)), 1)
        chat, name, data, _caption = send.call_args.args
        self.assertEqual(chat, 555)
        self.assertTrue(name.endswith(".json.gz"))
        import gzip
        self.assertIn("accounts.user", gzip.decompress(data).decode())
        self.assertTrue(BotState.get("backup_week"))


class ViewsTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_fan_and_card(self):
        fan = self.client.get(reverse("genealogy:fan_data_for", args=[self.user.username])).json()
        by_slot = {(x["gen"], x["slot"]): x["first"] for x in fan["people"]}
        self.assertEqual(by_slot[(0, 0)], "Timur")
        self.assertEqual((by_slot[(1, 0)], by_slot[(1, 1)]), ("Rustam", "Gulnora"))
        self.assertEqual((by_slot[(2, 0)], by_slot[(2, 1)]), ("Karim", "Malika"))
        card = self.client.get(reverse("genealogy:person_card", args=[self.p["me"].pk])).json()
        self.assertTrue(card["is_me"])
        self.assertEqual(card["can_add"], {"father": False, "mother": False, "spouse": True, "child": True, "sibling": True})
        self.assertEqual(card["child_surname"], {"son": "Rustamov", "daughter": "Nurmatov"})

    def test_quick_add_warns_about_duplicates(self):
        url = reverse("genealogy:quick_add", args=[self.p["me"].pk])
        response = self.client.post(url, {"relation": "child", "first_name": "Samir", "last_name": "Nurmatov", "gender": "male"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["duplicates"][0]["name"], "Samir Nurmatov")
        response = self.client.post(url, {"relation": "child", "first_name": "Samir", "last_name": "Nurmatov",
                                          "gender": "male", "confirm_duplicate": "on"})
        self.assertTrue(response.json()["ok"])
        child = Person.objects.get(pk=response.json()["id"])
        self.assertEqual((child.father, child.mother), (self.p["me"], self.p["wife"]))   # the only spouse is the mother

    def test_people_by_generation_timeline_and_dashboard(self):
        page = self.client.get(reverse("genealogy:people"))
        titles = [title for title, _rows in page.context["groups"]]
        self.assertEqual(len(titles), 5)                                      # grandparents … grandchildren
        self.assertEqual(page.context["groups"][0][1][0][0], self.p["grandpa"])
        missing = self.client.get(reverse("genealogy:people") + "?f=nodate")
        self.assertEqual([row[0] for _t, rows in missing.context["groups"] for row in rows], [self.p["grandson"]])
        timeline = self.client.get(reverse("genealogy:timeline"))
        self.assertContains(timeline, "Karim Nurmatov")
        self.assertEqual(timeline.context["decades"][0][0], 2010)             # newest decade first
        with mock.patch("apps.core.views.timezone.localdate", return_value=datetime.date(2026, 9, 27)):
            home = self.client.get(reverse("home"))
        self.assertEqual(home.context["today_items"][0]["person"], self.p["me"])
        self.assertTrue(home.context["today_items"][0]["share"].startswith("tg://msg?text="))
        self.assertLess(home.context["completeness"]["score"], 100)
        self.assertTrue(home.context["completeness"]["tasks"])

    def test_service_worker_and_offline(self):
        sw = self.client.get("/sw.js")
        self.assertEqual(sw["Service-Worker-Allowed"], "/")
        self.assertIn("showNotification", sw.content.decode())
        self.assertEqual(self.client.get(reverse("offline")).status_code, 200)


class AdminTests(TestCase):
    def test_admin_pages_open(self):
        user, p = make_family()
        user.is_staff = user.is_superuser = True
        user.save()
        self.client.force_login(user)
        for url in ("/admin/", f"/admin/accounts/user/{user.pk}/change/", "/admin/accounts/user/",
                    "/admin/accounts/membership/", "/admin/accounts/invite/", "/admin/genealogy/person/",
                    "/admin/genealogy/media/", "/admin/genealogy/change/", f"/admin/genealogy/person/{p['me'].pk}/change/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
