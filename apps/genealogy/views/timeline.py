"""Timeline: the family's years in order."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext as _

from ..kinship import Archive
from ..models import Event


TIMELINE_KINDS = ("birth", "wedding", "death", "event")


@login_required
def timeline(request):
    from apps.core.dates import format_partial_date

    archive = Archive(request.archive)
    show = request.GET.get("f", "")
    items = []

    def add(kind, year, month, day, text, url, person=None):
        if year and (not show or show == kind):
            items.append({"kind": kind, "year": year, "key": (year, month or 0, day or 0),
                          "when": format_partial_date(year, month, day), "text": text, "url": url, "person": person})

    for p in archive.people.values():
        add("birth", p.birth_year, p.birth_month, p.birth_day, _("{name} was born").format(name=p.short_name),
            p.get_absolute_url(), p)
        add("death", p.death_year, p.death_month, p.death_day, _("{name} passed away").format(name=p.short_name),
            p.get_absolute_url(), p)
    for m in archive.marriages:
        if m.husband_id in archive.people and m.wife_id in archive.people:
            husband, wife = archive.people[m.husband_id], archive.people[m.wife_id]
            add("wedding", m.year, m.month, m.day,
                _("Wedding of {a} and {b}").format(a=husband.short_name, b=wife.short_name),
                husband.get_absolute_url(), husband)
    for e in Event.objects.filter(owner=request.archive):
        add("event", e.year, e.month, e.day, e.display_title, e.get_absolute_url())
    items.sort(key=lambda i: i["key"], reverse=True)
    decades = {}
    for item in items:
        decades.setdefault(item["year"] // 10 * 10, []).append(item)
    return render(request, "genealogy/timeline.html", {
        "decades": list(decades.items()), "show": show, "total": len(items),
    })
