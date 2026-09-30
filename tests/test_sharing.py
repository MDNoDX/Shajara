"""Who may see and edit a family tree: strangers, viewers, editors, invitation links."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Invite, Membership, User
from apps.accounts.sharing import accept_invite, switch_archive
from apps.genealogy.models import Person

from .helpers import make_family


class AccessTests(TestCase):
    def setUp(self):
        self.owner, self.p = make_family()
        self.other = User.objects.create_user("begona", "b@example.com", "x-parol-12345", preferred_language="uz-cyrl")
        self.other.person = Person.objects.create(owner=self.other, first_name="Бегона", gender="male")
        self.other.save()
        self.client.force_login(self.other)

    def test_strangers_cannot_view(self):
        response = self.client.get(reverse("genealogy:person", args=[self.p["me"].pk]))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Кириш тақиқланган.", status_code=403)

    def test_viewers_can_view_but_not_edit(self):
        Membership.objects.create(owner=self.owner, member=self.other, role="viewer")
        self.assertEqual(self.client.get(reverse("genealogy:person", args=[self.p["me"].pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("genealogy:tree_for", args=[self.owner.username])).status_code, 200)
        response = self.client.get(reverse("genealogy:person_edit", args=[self.p["me"].pk]))
        self.assertContains(response, "Ушбу маълумотни ўзгартириш ҳуқуқингиз йўқ.", status_code=403)

    def test_invite_makes_a_shared_tree(self):
        invite = Invite.objects.create(owner=self.owner, created_by=self.owner, role="editor", person=self.p["cousin"])
        own_person = self.other.person
        # Opening the link and joining.
        self.assertEqual(self.client.get(reverse("accounts:invite", args=[invite.token])).status_code, 200)
        self.client.post(reverse("accounts:invite", args=[invite.token]))
        self.other.refresh_from_db()
        self.assertEqual(self.other.active_archive, self.owner)
        self.assertEqual(self.other.person, self.p["cousin"])       # who they are in the shared tree
        self.assertEqual(self.other.own_person, own_person)          # their own tree is kept
        invite.refresh_from_db()
        self.assertFalse(invite.is_open)                             # a link works once
        # The shared tree is named from the member's own place in it.
        data = self.client.get(reverse("genealogy:tree_data_for", args=[self.owner.username])).json()
        labels = {n["id"]: n["label"] for n in data["nodes"]}
        self.assertEqual(data["focus"], self.p["cousin"].pk)
        self.assertEqual(labels[self.p["cousin"].pk], "Сиз")
        # An editor adds a relative to the owner's archive; the change is in the history.
        response = self.client.post(reverse("genealogy:quick_add", args=[self.p["cousin"].pk]), {
            "relation": "child", "first_name": "Зарина", "gender": "female", "birth_year": "2010"})
        self.assertTrue(response.json()["ok"])
        child = Person.objects.get(first_name="Зарина")
        self.assertEqual((child.owner, child.mother), (self.owner, self.p["cousin"]))
        change = self.owner.changes.first()
        self.assertEqual((change.actor, change.person, change.action), (self.other, child, "created"))
        # Back to their own tree, and leaving.
        switch_archive(self.other, self.other)
        self.other.refresh_from_db()
        self.assertEqual((self.other.active_archive, self.other.person), (None, own_person))
        self.client.post(reverse("accounts:archive_leave", args=[self.owner.pk]))
        self.assertFalse(Membership.objects.filter(owner=self.owner, member=self.other).exists())

    def test_owner_manages_invites_and_members(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("accounts:family"), {"role": "viewer", "person": ""})
        invite = Invite.objects.get(owner=self.owner)
        page = self.client.get(reverse("accounts:family") + f"?yangi={invite.pk}").content.decode()
        self.assertIn(f"/taklif/{invite.token}/", page)
        accept_invite(invite, self.other)
        membership = Membership.objects.get(owner=self.owner, member=self.other)
        self.client.post(reverse("accounts:member_update", args=[membership.pk]), {"role": "editor"})
        membership.refresh_from_db()
        self.assertEqual(membership.role, "editor")
        self.client.post(reverse("accounts:member_update", args=[membership.pk]), {"remove": "1"})
        self.other.refresh_from_db()
        self.assertIsNone(self.other.active_archive)                 # pushed back to their own tree
        self.assertFalse(Membership.objects.filter(pk=membership.pk).exists())
