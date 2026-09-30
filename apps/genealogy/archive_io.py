"""Complete export and import of one user's family archive (JSON).

The export holds everything the user entered — people (with photos),
marriages, events, stories and friends — so the archive can be kept as a
backup or moved to another server or account:

    python manage.py import_archive shajara.json --user <username>
"""
import base64
import datetime

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.friends.models import Contact

from .models import Event, Marriage, Person, Story

FORMAT = "shajara-archive-1"
PERSON_FIELDS = [
    "first_name", "last_name", "patronymic", "gender", "birth_year", "birth_month", "birth_day", "birth_place",
    "is_deceased", "death_year", "death_month", "death_day", "death_place", "burial_place", "occupation",
    "education", "biography", "life_story",
]


def _photo(person):
    if not person.photo:
        return None
    try:
        with person.photo.open("rb") as f:
            data = f.read()
    except Exception:
        return None
    return {"name": person.photo.name.rsplit("/", 1)[-1], "data": base64.b64encode(data).decode()}


def export_archive(user):
    people = Person.objects.filter(owner=user).order_by("pk")
    return {
        "format": FORMAT,
        "exported_at": timezone.now().isoformat(),
        "owner": {"username": user.username, "first_name": user.first_name, "last_name": user.last_name,
                  "self": user.person_id},
        "people": [{"id": p.pk, "father": p.father_id, "mother": p.mother_id, "photo": _photo(p),
                    **{f: getattr(p, f) for f in PERSON_FIELDS}} for p in people],
        "marriages": [{"husband": m.husband_id, "wife": m.wife_id, "year": m.year, "month": m.month, "day": m.day}
                      for m in Marriage.objects.filter(owner=user)],
        "events": [{"kind": e.kind, "title": e.title, "year": e.year, "month": e.month, "day": e.day,
                    "place": e.place, "description": e.description, "every_year": e.every_year,
                    "people": list(e.people.values_list("pk", flat=True))}
                   for e in Event.objects.filter(owner=user).prefetch_related("people")],
        "stories": [{"title": s.title, "body": s.body, "year": s.year, "person": s.person_id}
                    for s in Story.objects.filter(owner=user)],
        "friends": [{"person": c.person_id, "name": c.name, "how_met": c.how_met, "phone": c.phone,
                     "birth_year": c.birth_year, "birth_month": c.birth_month, "birth_day": c.birth_day,
                     "note": c.note} for c in Contact.objects.filter(owner=user)],
    }


@transaction.atomic
def import_archive(user, data):
    """Add everything from an export to `user`'s archive. Returns counts."""
    if data.get("format") != FORMAT:
        raise ValueError("Not a Shajara archive file.")
    ids = {}
    for row in data["people"]:
        person = Person(owner=user, **{f: row.get(f) if row.get(f) is not None else Person._meta.get_field(f).get_default()
                                       for f in PERSON_FIELDS})
        person.save()
        if row.get("photo"):
            person.photo.save(row["photo"]["name"], ContentFile(base64.b64decode(row["photo"]["data"])), save=True)
        ids[row["id"]] = person
    for row in data["people"]:
        person = ids[row["id"]]
        person.father = ids.get(row.get("father"))
        person.mother = ids.get(row.get("mother"))
        person.save()
    for row in data.get("marriages", []):
        if row["husband"] in ids and row["wife"] in ids:
            Marriage.objects.get_or_create(owner=user, husband=ids[row["husband"]], wife=ids[row["wife"]],
                                           defaults={"year": row.get("year"), "month": row.get("month"),
                                                     "day": row.get("day")})
    for row in data.get("events", []):
        people = [ids[i] for i in row.pop("people", []) if i in ids]
        event = Event.objects.create(owner=user, **row)
        event.people.set(people)
    for row in data.get("stories", []):
        Story.objects.create(owner=user, title=row["title"], body=row["body"], year=row.get("year"),
                             person=ids.get(row.get("person")))
    for row in data.get("friends", []):
        if row.get("person") in ids:
            Contact.objects.create(owner=user, **{**row, "person": ids[row["person"]]})
    own = data.get("owner", {}).get("self")
    if own in ids and not user.person_id:
        user.person = ids[own]
        user.save(update_fields=["person"])
    return {"people": len(ids), "marriages": len(data.get("marriages", [])), "events": len(data.get("events", [])),
            "stories": len(data.get("stories", [])), "friends": len(data.get("friends", []))}


def export_filename():
    return f"shajara-{datetime.date.today().isoformat()}.json"
