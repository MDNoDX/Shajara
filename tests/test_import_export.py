"""GEDCOM import (round trip with the export)."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.genealogy import gedcom
from apps.genealogy.kinship import Archive
from apps.genealogy.models import Person

from .helpers import make_family


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
