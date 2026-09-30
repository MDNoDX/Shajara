"""The old "friend request" sharing becomes family-archive membership:
every accepted connection turns into view access in both directions."""
from django.db import migrations


def convert(apps, schema_editor):
    FriendRequest = apps.get_model("friends", "FriendRequest")
    Membership = apps.get_model("accounts", "Membership")
    for req in FriendRequest.objects.filter(status="accepted"):
        for owner_id, member_id in ((req.from_user_id, req.to_user_id), (req.to_user_id, req.from_user_id)):
            Membership.objects.get_or_create(owner_id=owner_id, member_id=member_id, defaults={"role": "viewer"})


class Migration(migrations.Migration):
    dependencies = [
        ("friends", "0002_contact"),
        ("accounts", "0005_collaboration"),
    ]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
        migrations.DeleteModel(name="FriendRequest"),
    ]
