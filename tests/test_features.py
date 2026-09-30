"""Muchal, reminders, Telegram linking, events, friends, calculator, GEDCOM."""
import datetime
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from apps.core.muchal import muchal, next_muchal_year
from apps.core.text import surname_from_name
from apps.friends.models import Contact
from apps.genealogy import gedcom
from apps.genealogy.kinship import Archive
from apps.genealogy.models import Event, Person
from apps.notify import service, telegram
from apps.notify.messages import render_parts
from apps.notify.models import Notification, NotificationSettings
from apps.notify.occasions import occasions

from .helpers import make_family


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


class ReminderTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.today = datetime.date(2026, 9, 26)  # the day before Timur's birthday (27 September)

    def test_occasions_cover_every_kind(self):
        self.p["grandpa"].death_month, self.p["grandpa"].death_day = 9, 30
        self.p["grandpa"].save()
        m = self.p["me"].marriages_as_husband.first()
        m.year, m.month, m.day = 2010, 10, 1
        m.save()
        Contact.objects.create(owner=self.user, person=self.p["me"], name="Jasur", birth_month=9, birth_day=28)
        e = Event.objects.create(owner=self.user, kind="wedding", year=2026, month=9, day=29)
        e.people.add(self.p["son"])
        kinds = {o.kind for o in occasions(self.user, self.today, self.today + datetime.timedelta(days=10))}
        self.assertEqual(kinds, {"birthday", "friend_birthday", "memorial", "anniversary", "event"})

    def test_generate_is_idempotent_and_respects_lead_time(self):
        prefs = NotificationSettings.for_user(self.user)
        prefs.days_before = 1
        prefs.save()
        self.assertEqual(service.generate(self.user, self.today), 1)   # "tomorrow" reminder
        self.assertEqual(service.generate(self.user, self.today), 0)   # not twice
        self.assertEqual(service.generate(self.user, self.today + datetime.timedelta(days=1)), 1)  # "today"
        note = Notification.objects.filter(user=self.user).order_by("created_at").first()
        with translation.override("uz"):
            self.assertEqual(note.text["title"], "Tugʻilgan kun: Timur Nurmatov")
            self.assertEqual(note.text["body"], "Ertaga 42 yoshga toʻladi.")
        with translation.override("uz-cyrl"):
            self.assertEqual(note.text["body"], "Эртага 42 ёшга тўлади.")

    def test_disabled_and_filtered(self):
        prefs = NotificationSettings.for_user(self.user)
        prefs.birthdays = False
        prefs.save()
        self.assertEqual(service.generate(self.user, self.today + datetime.timedelta(days=1)), 0)
        prefs.birthdays, prefs.enabled = True, False
        prefs.save()
        self.assertEqual(service.generate(self.user, self.today + datetime.timedelta(days=1)), 0)

    def test_muchal_at_navroz(self):
        o = [x for x in occasions(self.user, datetime.date(2030, 3, 21), datetime.date(2030, 3, 21)) if x.kind == "muchal"]
        # 2030 is a Dog year: Nigora (1982) is a Dog, Timur (1984) is a Rat.
        self.assertIn("Nigora Karimova", o[0].params["names"])
        self.assertNotIn("Timur Nurmatov", o[0].params["names"])
        o = [x for x in occasions(self.user, datetime.date(2032, 3, 21), datetime.date(2032, 3, 21)) if x.kind == "muchal"]
        self.assertIn("Timur Nurmatov", o[0].params["names"])  # 2032 is a Rat year
        with translation.override("uz"):
            self.assertIn("Sichqon", render_parts("muchal", o[0].params)["title"])

    def test_bell_and_pages(self):
        self.client.force_login(self.user)
        with mock.patch("apps.notify.service.timezone.localdate", return_value=self.today + datetime.timedelta(days=1)):
            html = self.client.get(reverse("home")).content.decode()
        self.assertIn('class="dot-badge"', html)
        note = Notification.objects.get(user=self.user)
        self.client.get(reverse("notify:open", args=[note.pk]))
        note.refresh_from_db()
        self.assertIsNotNone(note.read_at)


@override_settings(TELEGRAM_BOT_TOKEN="123:abc", TELEGRAM_BOT_USERNAME="shajara_test_bot")
class TelegramTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.prefs = NotificationSettings.for_user(self.user)

    def test_link_and_send(self):
        url = telegram.link_url(self.prefs)
        token = url.rsplit("=", 1)[1]
        self.assertTrue(url.startswith("https://t.me/shajara_test_bot?start="))
        sent = []
        with mock.patch("apps.notify.telegram.send_message", side_effect=lambda chat, text: sent.append((chat, text))):
            telegram.handle_update({"update_id": 1, "message": {"text": f"/start {token}",
                                                                "chat": {"id": 555, "type": "private", "username": "timur"}}})
            self.prefs.refresh_from_db()
            self.assertEqual(self.prefs.telegram_chat_id, 555)
            self.assertTrue(self.prefs.telegram_enabled)
            self.assertIn("Hisobingiz ulandi", sent[-1][1])
            # The token works only once.
            telegram.handle_update({"update_id": 2, "message": {"text": f"/start {token}",
                                                                "chat": {"id": 777, "type": "private"}}})
            self.assertIn("muddati tugagan", sent[-1][1])

            service.generate(self.user, datetime.date(2026, 9, 27))
            with mock.patch("apps.notify.service.timezone.localtime") as lt:
                lt.return_value = datetime.datetime(2026, 9, 27, 9, 0)
                self.assertEqual(service.send_pending_telegram(), 1)
            self.assertIn("<b>Tugʻilgan kun: Timur Nurmatov</b>", sent[-1][1])

            telegram.handle_update({"update_id": 3, "message": {"text": "/stop", "chat": {"id": 555, "type": "private"}}})
            self.prefs.refresh_from_db()
            self.assertFalse(self.prefs.telegram_enabled)


class EventsFriendsTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def test_create_future_event(self):
        response = self.client.post(reverse("genealogy:event_create"), {
            "kind": "wedding", "title": "Samirning to'yi", "people": [self.p["son"].pk],
            "event_day": "15", "event_month": "8", "event_year": str(datetime.date.today().year + 1),
        })
        event = Event.objects.get()
        self.assertRedirects(response, event.get_absolute_url())
        self.assertEqual(event.title, "Samirning toʻyi")
        self.assertEqual(list(event.people.all()), [self.p["son"]])

    def test_every_year_needs_day_and_month(self):
        response = self.client.post(reverse("genealogy:event_create"), {
            "kind": "memorial", "every_year": "on", "event_year": "2001",
        })
        self.assertContains(response, "Har yili eslatilishi uchun kun va oyni kiriting.")

    def test_friend_of_father(self):
        response = self.client.post(reverse("friends:create"), {
            "person": self.p["father"].pk, "name": "Baxtiyor", "how_met": "army", "birth_day": "3", "birth_month": "5",
        })
        self.assertEqual(response.status_code, 302)
        contact = Contact.objects.get()
        self.assertEqual((contact.person, contact.birth_year, contact.birth_month), (self.p["father"], None, 5))
        html = self.client.get(reverse("genealogy:person", args=[self.p["father"].pk])).content.decode()
        self.assertIn("Baxtiyor", html)
        self.assertIn("Harbiy xizmatdosh", html)

    def test_calculator_and_person_page(self):
        html = self.client.get(reverse("genealogy:calculator"),
                               {"a": self.p["me"].pk, "b": self.p["cousin"].pk}).content.decode()
        self.assertIn("Ammavachcha", html)
        html = self.client.get(reverse("genealogy:person", args=[self.p["me"].pk])).content.decode()
        self.assertIn("Muchali", html)
        self.assertIn("Sichqon", html)  # 1984

    def test_gedcom(self):
        text = gedcom.export(Archive(self.user), "Timur")
        self.assertTrue(text.startswith("0 HEAD"))
        self.assertIn(f"0 @I{self.p['me'].pk}@ INDI", text)
        self.assertIn("2 DATE 27 SEP 1984", text)
        self.assertIn(f"1 CHIL @I{self.p['me'].pk}@", text)
        self.assertTrue(text.rstrip().endswith("0 TRLR"))
        response = self.client.get(reverse("genealogy:gedcom"))
        self.assertIn(".ged", response["Content-Disposition"])

    def test_path(self):
        a = Archive(self.user)
        chain = a.path(self.p["me"].pk, self.p["cousin"].pk)
        self.assertEqual(chain[0], self.p["me"].pk)
        self.assertEqual(chain[-1], self.p["cousin"].pk)
        self.assertEqual(len(chain), 5)  # me → father → grandpa → aunt → cousin

    def test_son_surname_suggestion(self):
        html = self.client.get(reverse("genealogy:relative_add", args=[self.p["me"].pk]) + "?relation=child").content.decode()
        self.assertIn('data-son-surname="Rustamov"', html)


class LiveSearchTests(TestCase):
    def setUp(self):
        self.user, self.p = make_family()
        self.client.force_login(self.user)

    def search(self, q, **extra):
        return self.client.get(reverse("genealogy:search_json"), {"q": q, **extra}).json()["results"]

    def test_cross_script_and_ranking(self):
        Person.objects.create(owner=self.user, first_name="Olim", last_name="Laylov", gender="male")
        names = [r["name"] for r in self.search("Лайло")]
        self.assertEqual(names[0], "Nurmatova Laylo")          # first-name match first
        self.assertIn("Laylov Olim", names)
        first = self.search("lay")[0]
        self.assertEqual((first["label"], first["url"]), ("Singil", self.p["younger_sister"].get_absolute_url()))

    def test_partial_pages(self):
        html = self.client.get(reverse("genealogy:search"), {"q": "kam", "partial": 1}).content.decode()
        self.assertNotIn("<html", html)
        self.assertIn("Kamila Aliyeva", html)
        html = self.client.get(reverse("genealogy:people"), {"q": "aziza", "partial": 1}).content.decode()
        self.assertIn("Aziza Nurmatova", html)
        self.assertNotIn("Kamila", html)

    def test_other_archives_are_private(self):
        from apps.accounts.models import User

        stranger = User.objects.create_user("begona2", "b2@example.com", "x-parol-12345")
        response = self.client.get(reverse("genealogy:search_json"), {"q": "a", "owner": stranger.username})
        self.assertEqual(response.status_code, 403)

    def test_no_divorce_option(self):
        m = self.p["me"].marriages_as_husband.first()
        html = self.client.get(reverse("genealogy:marriage_edit", args=[m.pk])).content.decode()
        self.assertNotIn("is_divorced", html)
