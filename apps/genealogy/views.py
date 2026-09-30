import datetime
import json
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from apps.core.text import search_tokens

from apps.core.muchal import next_muchal_year
from apps.core.text import surname_from_name
from apps.notify.messages import render_parts
from apps.notify.occasions import occasions

from . import archive_io, duplicates, gedcom, history, pdf
from .access import (archive_owner, can_edit, can_view, person_for_edit, person_for_view, require_edit,
                     story_for_edit, story_for_view, viewer_person)
from .forms import EventForm, MarriageForm, PersonForm, RelativeWithSpouseForm, StoryForm
from .kinship import Archive
from .models import Change, Event, Marriage, Media, Person, Story
from .terminology import ADD_RELATION, BRANCHES, SECTION, generation_label
from .tree import build_tree


def _focus_for(request, archive, requested=None):
    """The person in the centre: the one asked for, else the viewer's own
    record, else the archive owner's, else anyone."""
    if requested:
        try:
            pk = int(requested)
        except (TypeError, ValueError):
            pk = None
        if pk in archive.people:
            return pk
    me = viewer_person(request, archive)
    return me if me is not None else next(iter(archive.people), None)


def _ids(value):
    out = set()
    for part in (value or "").split(","):
        if part.strip().isdigit() and len(out) < 500:
            out.add(int(part))
    return out


def _tree_state(request):
    """Which branches are open: ?all=1&open=…&closed=…&folded=…&kids=… (comma-separated ids)."""
    return {
        "open_all": request.GET.get("all") == "1",
        "opened": _ids(request.GET.get("open")),
        "closed": _ids(request.GET.get("closed")),
        "folded": _ids(request.GET.get("folded")),
        "unfolded": _ids(request.GET.get("kids")),
        "side": request.GET.get("side") if request.GET.get("side") in ("paternal", "maternal") else None,
    }


def _pdf_response(data, filename):
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = content_disposition_header(True, filename)
    return response


def _search(queryset, query):
    for token in search_tokens(query):
        queryset = queryset.filter(search_key__contains=token)
    return queryset


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------
def _filter_people(queryset, show):
    """The chips above the list of people, and the "what is missing" links of the dashboard."""
    from django.db.models import Q

    rules = {
        "living": Q(is_deceased=False),
        "deceased": Q(is_deceased=True),
        "male": Q(gender="male"),
        "female": Q(gender="female"),
        "nodate": Q(birth_year=None),
        "noday": Q(is_deceased=False, birth_year__isnull=False) & (Q(birth_month=None) | Q(birth_day=None)),
        "nophoto": Q(photo=""),
        "nostory": Q(is_deceased=True, biography="", life_story=""),
    }
    return queryset.filter(rules[show]) if show in rules else queryset


MISSING_FILTERS = ("nodate", "noday", "nophoto", "nostory", "unlinked")


@login_required
def people_list(request):
    """Everyone in the archive: by generation and side of the family, or A–Z."""
    query = request.GET.get("q", "").strip()
    show = request.GET.get("f", "")
    order = "abc" if request.GET.get("tartib") == "abc" else "gen"
    archive = Archive(request.archive)
    people = _filter_people(Person.objects.filter(owner=request.archive), show)
    focus = _focus_for(request, archive)
    branches = archive.branches(focus) if focus else {}
    if show == "unlinked" and focus:
        people = people.exclude(pk__in=list(archive.generations(focus)))

    def row(p):
        return (p, archive.label(focus, p.pk) if focus else "", branches.get(p.pk, "other"))

    groups = []
    if query:
        groups = [("", [row(p) for p in _ranked(people, query, 500)])]
    elif order == "abc" or not focus or show in MISSING_FILTERS:
        groups = [("", [row(p) for p in people.order_by("first_name", "last_name", "id")])]
    else:
        gens = archive.generations(focus)
        side_order = {"own": 0, "paternal": 1, "maternal": 2, "other": 3}
        by_gen = {}
        for p in people:
            key = max(-3, min(3, gens[p.pk])) if p.pk in gens else None
            by_gen.setdefault(key, []).append(p)
        for key in sorted((k for k in by_gen if k is not None)) + ([None] if None in by_gen else []):
            members = sorted(by_gen[key], key=lambda p: (side_order[branches.get(p.pk, "other")],
                                                         p.birth_key or (9999,), p.first_name))
            label = generation_label(key) if key is not None else _("Not yet linked to the family")
            groups.append((label, [row(p) for p in members]))
    template = "genealogy/_people_grid.html" if request.GET.get("partial") else "genealogy/people_list.html"
    return render(request, template, {
        "groups": groups, "query": query, "total": len(archive.people), "show": show, "order": order,
        "missing": show in MISSING_FILTERS,
        "shown": sum(len(rows) for _label, rows in groups),
        "duplicates": len(duplicates.pairs(request.archive)) if request.can_edit and not request.GET.get("partial") else 0,
    })


def _life_path(archive, person):
    """The milestones of one life, oldest first: [{"year", "when", "kind", "text", "url"}]."""
    items = []

    def add(year, month, day, kind, text, url=""):
        from apps.core.dates import format_partial_date

        items.append({"key": (year or 9999, month or 0, day or 0), "year": year,
                      "when": format_partial_date(year, month, day) if year else "", "kind": kind,
                      "text": text, "url": url})

    if person.birth_year:
        add(person.birth_year, person.birth_month, person.birth_day, "birth",
            _("Born in {place}").format(place=person.birth_place) if person.birth_place else _("Born"))
    for partner_id, m in archive.unions.get(person.pk, []):
        partner = archive.people[partner_id]
        if m.year:
            add(m.year, m.month, m.day, "wedding", _("Married {name}").format(name=partner.short_name),
                partner.get_absolute_url())
    for child_id in archive.children.get(person.pk, []):
        child = archive.people[child_id]
        if child.birth_year:
            text = (_("Son {name} was born") if child.is_male else _("Daughter {name} was born")).format(
                name=child.first_name)
            add(child.birth_year, child.birth_month, child.birth_day, "child", text, child.get_absolute_url())
    for event in person.events.all():
        if event.year:
            add(event.year, event.month, event.day, "event", event.display_title, event.get_absolute_url())
    if person.death_year:
        add(person.death_year, person.death_month, person.death_day, "death",
            _("Passed away in {place}").format(place=person.death_place) if person.death_place else _("Passed away"))
    items.sort(key=lambda i: i["key"])
    if person.birth_year:
        for item in items:
            if item["kind"] not in ("birth",) and item["year"]:
                item["age"] = item["year"] - person.birth_year
    return items


def _prompts(person, is_me):
    """Questions that invite the family to fill in what is still missing."""
    out = []
    if not person.birth_year:
        out.append(("birth", _("When was {name} born? Even the year alone helps.")))
    elif not (person.birth_month and person.birth_day) and not person.is_deceased:
        out.append(("birth", _("Add the day and month of birth to be reminded of {name}’s birthday.")))
    if not person.birth_place:
        out.append(("place", _("Where was {name} born?")))
    if not person.photo:
        out.append(("photo", _("Add a photo of {name}: faces make the family tree come alive.")))
    if not person.occupation and not person.is_deceased and not is_me:
        out.append(("work", _("What does {name} do?")))
    if person.is_deceased and not person.occupation:
        out.append(("work", _("What did {name} do in life?")))
    return [(kind, text.format(name=person.first_name)) for kind, text in out[:3]]


@login_required
def person_detail(request, pk):
    person = person_for_view(request, pk)
    archive = Archive(person.owner)
    editable = can_edit(request.user, person.owner)
    me = viewer_person(request, archive)

    def people(pks):
        return [(archive.people[x], archive.label(person.pk, x)) for x in pks]

    media = list(person.media.all())
    context = {
        "person": person,
        "is_owner": editable,
        "relation_to_me": archive.label(me, person.pk) if me and me != person.pk else "",
        "branch": archive.branches(me).get(person.pk, "other") if me else "own",
        "father": archive.people.get(person.father_id),
        "mother": archive.people.get(person.mother_id),
        "spouses": people(archive.spouses(person.pk)),
        "marriages": [m for _sid, m in archive.unions.get(person.pk, [])],
        "children": people(archive.children.get(person.pk, [])),
        "siblings": people(archive.siblings(person.pk)),
        "stories": person.stories.all(),
        "events": person.events.all(),
        "friends": person.friends.all(),
        "photos": [m for m in media if m.kind == Media.Kind.PHOTO],
        "files": [m for m in media if m.kind != Media.Kind.PHOTO],
        "media_count": len(media),
        "life_path": _life_path(archive, person),
        "prompts": _prompts(person, request.user.person_id == person.pk) if editable else [],
        "muchal": person.muchal,
        "next_muchal": next_muchal_year(person.birth_year, person.birth_month, person.birth_day)
        if not person.is_deceased else None,
        "section": SECTION,
        "add_relation": ADD_RELATION,
        "is_me": request.user.person_id == person.pk,
        "can_be_me": (request.user.person_id != person.pk and person.owner_id == request.archive.pk
                      and not hasattr(person, "account")),
        "changes": person.changes.select_related("actor")[:5] if editable else [],
    }
    return render(request, "genealogy/person_detail.html", context)


@login_required
def person_create(request):
    owner = require_edit(request)
    form = PersonForm(request.POST or None, request.FILES or None, owner=owner, archive=Archive(owner))
    if request.method == "POST" and form.is_valid():
        person = form.save()
        history.record(owner, request.user, Change.Action.CREATED, person)
        messages.success(request, _("The person has been added to the family tree."))
        return redirect(person)
    return render(request, "genealogy/person_form.html", {"form": form, "is_new": True})


@login_required
def person_edit(request, pk):
    person = person_for_edit(request, pk)
    archive = Archive(person.owner)
    before = history.snapshot(person)
    form = PersonForm(request.POST or None, request.FILES or None, instance=person, owner=person.owner, archive=archive)
    if request.method == "POST" and form.is_valid():
        person = form.save()
        history.record_update(request.user, person, before)
        messages.success(request, _("The information has been saved."))
        return redirect(person)
    return render(request, "genealogy/person_form.html", {"form": form, "person": person, "is_new": False})


def _linked_to_account(person):
    from apps.accounts.models import Membership, User

    return (User.objects.filter(person=person).exists() or User.objects.filter(own_person=person).exists()
            or Membership.objects.filter(person=person).exists())


@login_required
def person_delete(request, pk):
    person = person_for_edit(request, pk)
    if request.user.person_id == person.pk:
        messages.error(request, _("Your own record cannot be deleted."))
        return redirect(person)
    if _linked_to_account(person):
        messages.error(request, _("This record belongs to a relative who has an account, so it cannot be deleted."))
        return redirect(person)
    if request.method == "POST":
        history.record_delete(request.user, person)
        person.delete()
        messages.success(request, _("The record has been deleted. It can be restored from the history."))
        return redirect("genealogy:people")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": person.full_name, "cancel_url": person.get_absolute_url(), "restorable": True,
    })


def _relative_form(request, anchor, data=None, files=None, initial=None):
    archive = Archive(anchor.owner)
    spouses = [archive.people[sp] for sp in archive.spouses(anchor.pk)]
    form = RelativeWithSpouseForm(data, files, owner=anchor.owner, archive=archive, anchor=anchor, spouses=spouses,
                                  initial=initial or {})
    return form, archive, spouses


def _save_relative(request, form, anchor):
    existing = form.cleaned_data.get("existing")
    before = history.snapshot(existing) if existing else None
    anchor_before = history.snapshot(anchor)
    person = form.save()
    if existing:
        history.record(anchor.owner, request.user, Change.Action.LINKED, person,
                       details={"relation": form.cleaned_data["relation"], "to": anchor.short_name},
                       before=None)
        history.record_update(request.user, person, before)
    else:
        history.record(anchor.owner, request.user, Change.Action.CREATED, person,
                       details={"relation": form.cleaned_data["relation"], "to": anchor.short_name})
    anchor.refresh_from_db()
    history.record_update(request.user, anchor, anchor_before)
    return person


@login_required
def relative_add(request, pk):
    anchor = person_for_edit(request, pk)
    initial = {}
    relation = request.GET.get("relation")
    if relation in ADD_RELATION:
        initial["relation"] = relation
        if relation == "father":
            initial["gender"] = "male"
        elif relation == "mother":
            initial["gender"] = "female"
        if relation == "sibling":
            initial["last_name"] = anchor.last_name
    form, archive, spouses = _relative_form(request, anchor, request.POST or None, request.FILES or None, initial)
    if request.method == "POST" and form.is_valid():
        _save_relative(request, form, anchor)
        messages.success(request, _("The person has been added to the family tree."))
        return redirect(anchor)
    # A son takes his paternal grandfather's name as surname (Madaminjon → Madaminov).
    grandfather = archive.people.get(anchor.father_id) if anchor.is_male else None
    return render(request, "genealogy/relative_form.html", {
        "form": form, "anchor": anchor, "has_spouses": bool(spouses),
        "son_surname": surname_from_name(grandfather.first_name) if grandfather else "",
        "father_surname": anchor.last_name,
    })


@login_required
def marriage_edit(request, pk):
    marriage = get_object_or_404(Marriage, pk=pk)
    require_edit(request, marriage.owner)
    back = request.GET.get("from") or marriage.husband_id
    form = MarriageForm(request.POST or None, instance=marriage)
    if request.method == "POST":
        names = f"{marriage.husband.short_name} · {marriage.wife.short_name}"
        if "delete" in request.POST:
            marriage.delete()
            history.record(marriage.owner, request.user, Change.Action.DELETED, subject=names, what="marriage")
            messages.success(request, _("The marriage record has been deleted."))
            return redirect("genealogy:person", pk=back)
        if form.is_valid():
            form.save()
            history.record(marriage.owner, request.user, Change.Action.UPDATED, subject=names, what="marriage")
            messages.success(request, _("The information has been saved."))
            return redirect("genealogy:person", pk=back)
    return render(request, "genealogy/marriage_form.html", {"form": form, "marriage": marriage, "back": back})


@login_required
def person_pdf(request, pk):
    person = person_for_view(request, pk)
    archive = Archive(person.owner)
    data = pdf.person_pdf(archive, person, focus_id=viewer_person(request, archive),
                          stories=list(person.stories.all()))
    return _pdf_response(data, f"{person.short_name}.pdf")


# ---------------------------------------------------------------------------
# Album: photos, documents and voice recordings of a person
# ---------------------------------------------------------------------------
MEDIA_MAX_BYTES = 12 * 1024 * 1024
DOCUMENT_TYPES = ("application/pdf",)


@require_POST
@login_required
def media_upload(request, pk):
    from django.core.files.base import ContentFile

    from apps.core.images import shrink

    person = person_for_edit(request, pk)
    added = 0
    for upload in request.FILES.getlist("files")[:20]:
        if upload.size > MEDIA_MAX_BYTES:
            messages.error(request, _("“{name}” is too large.").format(name=upload.name))
            continue
        kind, content = None, None
        ctype = (upload.content_type or "").lower()
        if ctype.startswith("image/"):
            small = shrink(upload)
            if small:
                content, ext = small
                content.name = f"photo.{ext}"
                kind = Media.Kind.PHOTO
        elif ctype.startswith("audio/"):
            kind, content = Media.Kind.AUDIO, ContentFile(upload.read(), name=upload.name)
        elif ctype in DOCUMENT_TYPES:
            kind, content = Media.Kind.DOCUMENT, ContentFile(upload.read(), name=upload.name)
        if kind is None:
            messages.error(request, _("“{name}” is not a photo, a PDF document or a recording.").format(name=upload.name))
            continue
        year = request.POST.get("year", "")
        Media.objects.create(owner=person.owner, person=person, kind=kind, file=content,
                             caption=request.POST.get("caption", "").strip()[:200],
                             year=int(year) if year.isdigit() and 1000 <= int(year) <= 2200 else None,
                             uploaded_by=request.user)
        added += 1
    if added:
        history.record(person.owner, request.user, Change.Action.UPDATED, person, what="album",
                       details={"added": added})
        messages.success(request, _("Added to the album."))
    return redirect(person.get_absolute_url() + "#album")


def _media_for_edit(request, pk):
    item = get_object_or_404(Media.objects.select_related("person", "owner"), pk=pk)
    require_edit(request, item.owner)
    return item


@require_POST
@login_required
def media_delete(request, pk):
    item = _media_for_edit(request, pk)
    person = item.person
    if person.photo and person.photo.name == item.file.name:
        person.photo = ""
        person.save(update_fields=["photo", "updated_at"])
    item.file.delete(save=False)
    item.delete()
    messages.success(request, _("The record has been deleted."))
    return redirect(person.get_absolute_url() + "#album")


@require_POST
@login_required
def media_portrait(request, pk):
    """Use an album photo as the person's main photo."""
    item = _media_for_edit(request, pk)
    if item.kind == Media.Kind.PHOTO:
        before = history.snapshot(item.person)
        item.person.photo = item.file.name
        item.person.save(update_fields=["photo", "updated_at"])
        history.record_update(request.user, item.person, before)
        messages.success(request, _("The information has been saved."))
    return redirect(item.person)


# ---------------------------------------------------------------------------
# Duplicates and history
# ---------------------------------------------------------------------------
@login_required
def duplicates_page(request):
    owner = require_edit(request)
    archive = Archive(owner)
    focus = _focus_for(request, archive)
    pairs = [[(p, archive.label(focus, p.pk) if focus else "") for p in pair] for pair in duplicates.pairs(owner)]
    return render(request, "genealogy/duplicates.html", {"pairs": pairs})


@require_POST
@login_required
def merge_people(request):
    owner = require_edit(request)
    keep = get_object_or_404(Person, pk=request.POST.get("keep"), owner=owner)
    drop = get_object_or_404(Person, pk=request.POST.get("drop"), owner=owner)
    if drop.pk == request.user.person_id:
        keep, drop = drop, keep
    if duplicates.merge(keep, drop, request.user):
        messages.success(request, _("The two records have been merged."))
    return redirect("genealogy:duplicates")


@login_required
def history_page(request):
    changes = Change.objects.filter(owner=request.archive).select_related("actor", "person")[:200]
    labels = {f.name: f.verbose_name for f in Person._meta.fields}
    labels.update({"father_id": labels["father"], "mother_id": labels["mother"]})
    rows = []
    for change in changes:
        fields = [str(labels.get(name, name)) for name in (change.details or {}).get("fields", {})]
        rows.append((change, fields))
    return render(request, "genealogy/history.html", {"rows": rows, "can_undo": request.can_edit})


@require_POST
@login_required
def history_undo(request, pk):
    change = get_object_or_404(Change, pk=pk)
    require_edit(request, change.owner)
    person = history.undo(change, request.user)
    if person is None:
        messages.error(request, _("This change can no longer be undone."))
        return redirect("genealogy:history")
    messages.success(request, _("Restored."))
    return redirect(person)


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------
@login_required
def tree_page(request, username=None):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(request, archive, request.GET.get("person"))
    editable = can_edit(request.user, owner)
    return render(request, "genealogy/tree.html", {
        "owner": owner,
        "is_owner": editable,
        "is_active_archive": owner.pk == request.archive.pk,
        "focus": archive.people.get(focus),
        "data_url": reverse("genealogy:tree_data_for", args=[owner.username]),
        "fan_url": reverse("genealogy:fan_data_for", args=[owner.username]),
        "pdf_url": reverse("genealogy:tree_pdf_for", args=[owner.username]),
        "add_relation": ADD_RELATION,
        "branches": BRANCHES,
    })


@login_required
def tree_data(request, username):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(request, archive, request.GET.get("person"))
    if focus is None:
        return JsonResponse({"nodes": [], "lines": [], "rows": [], "width": 0, "height": 0, "focus": None})
    return JsonResponse(build_tree(archive, focus, viewer_person=viewer_person(request, archive),
                                   **_tree_state(request)))


@login_required
def fan_data(request, username):
    """Ancestors of the centre person for the fan chart: generation rings,
    each person at slot 0 … 2^generation − 1 (father before mother)."""
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(request, archive, request.GET.get("person"))
    if focus is None:
        return JsonResponse({"people": [], "generations": 0, "focus": None})
    depth = 6
    out, level = [], [(focus, 0)]
    for generation in range(depth + 1):
        nxt = []
        for pk, slot in level:
            person = archive.people[pk]
            out.append({"id": pk, "gen": generation, "slot": slot, "name": person.short_name,
                        "first": person.first_name, "years": person.lifespan, "gender": person.gender,
                        "url": person.get_absolute_url(), "label": archive.label(focus, pk) if pk != focus else ""})
            if person.father_id in archive.people:
                nxt.append((person.father_id, slot * 2))
            if person.mother_id in archive.people:
                nxt.append((person.mother_id, slot * 2 + 1))
        level = nxt
        if not level:
            break
    return JsonResponse({"people": out, "generations": max(p["gen"] for p in out), "focus": focus,
                         "focus_name": archive.people[focus].short_name})


@login_required
def person_card(request, pk):
    """What the side panel of the tree shows about one person."""
    person = person_for_view(request, pk)
    archive = Archive(person.owner)
    me = viewer_person(request, archive)
    editable = can_edit(request.user, person.owner)
    has_parents = bool(person.father_id or person.mother_id)
    can_add = {"father": not person.father_id, "mother": not person.mother_id, "spouse": True, "child": True,
               "sibling": has_parents} if editable else {}
    return JsonResponse({
        "id": person.pk, "name": person.short_name, "full_name": person.full_name, "initials": person.initials,
        "gender": person.gender, "years": person.lifespan, "deceased": person.is_deceased,
        "born": person.birth_date_display, "birth_place": person.birth_place,
        "died": person.death_date_display, "occupation": person.occupation,
        "label": archive.label(me, person.pk) if me and me != person.pk else "",
        "is_me": person.pk == request.user.person_id,
        "photo": person.photo.url if person.photo else "", "url": person.get_absolute_url(),
        "edit_url": reverse("genealogy:person_edit", args=[person.pk]) if editable else "",
        "more_url": reverse("genealogy:relative_add", args=[person.pk]) if editable else "",
        "add_url": reverse("genealogy:quick_add", args=[person.pk]) if editable else "",
        "can_add": can_add, "last_name": person.last_name,
        "child_surname": _child_surname(archive, person),
        "counts": {"children": len(archive.children.get(person.pk, [])),
                   "siblings": len(archive.siblings(person.pk)), "spouses": len(archive.spouses(person.pk))},
    })


def _child_surname(archive, person):
    """Surnames suggested for a child of `person`: a son takes the name of his
    paternal grandfather (Madaminjon → Madaminov), a daughter her father's surname."""
    father = person
    if not person.is_male:
        spouses = archive.spouses(person.pk)
        father = archive.people[spouses[0]] if len(spouses) == 1 else None
    if father is None:
        return {"son": "", "daughter": ""}
    grandfather = archive.people.get(father.father_id)
    return {"son": surname_from_name(grandfather.first_name) if grandfather else father.last_name,
            "daughter": father.last_name}


@require_POST
@login_required
def quick_add(request, pk):
    """Add a relative from the tree itself (name, gender and birth year are enough)."""
    anchor = person_for_edit(request, pk)
    data = request.POST.copy()
    archive = Archive(anchor.owner)
    spouses = archive.spouses(anchor.pk)
    if data.get("relation") == "child" and not data.get("other_parent") and len(spouses) == 1:
        data["other_parent"] = str(spouses[0])
    form, _archive, _spouses = _relative_form(request, anchor, data)
    if form.is_valid():
        person = _save_relative(request, form, anchor)
        return JsonResponse({"ok": True, "id": person.pk, "name": person.short_name})
    errors = {name: [str(e) for e in errs] for name, errs in form.errors.items()}
    return JsonResponse({
        "ok": False, "errors": errors,
        "duplicates": [{"id": p.pk, "name": p.short_name, "years": p.lifespan, "url": p.get_absolute_url()}
                       for p in form.duplicates],
    }, status=400)


@login_required
def tree_pdf(request, username):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(request, archive, request.GET.get("person"))
    if focus is None:
        raise Http404(_("The family tree is empty."))
    layout = build_tree(archive, focus, photo_urls=False, viewer_person=viewer_person(request, archive),
                        **_tree_state(request))
    person = archive.people[focus]
    subtitle = _("Centred on %(name)s. Relationship names are given as seen from this person.") % {
        "name": person.full_name}
    size = request.GET.get("size", "").upper()
    data = pdf.tree_pdf(layout, _("Family tree"), subtitle, poster=size if size in pdf.POSTER_SIZES else None,
                        family=_family_name(archive, focus), photos=pdf.tree_photos(archive, layout))
    name = pgettext("file name", "family-tree") + (f"-{size}" if size in pdf.POSTER_SIZES else "")
    return _pdf_response(data, name + ".pdf")


def _family_name(archive, focus):
    """The surname the book and the poster are titled with."""
    person = archive.people.get(focus)
    if person is None:
        return ""
    if person.last_name:
        return _("The {name} family").format(name=person.last_name)
    return person.first_name


@login_required
def family_book(request, username=None):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(request, archive)
    if focus is None:
        raise Http404(_("The family tree is empty."))
    data = pdf.family_book_pdf(archive, focus, owner.display_name,
                               viewer_is_owner=viewer_person(request, archive) == focus,
                               family=_family_name(archive, focus))
    return _pdf_response(data, pgettext("file name", "family-book") + ".pdf")


# ---------------------------------------------------------------------------
# Timeline: the family's years in order
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------
@login_required
def story_list(request):
    stories = Story.objects.filter(owner=request.archive).select_related("person")
    return render(request, "genealogy/story_list.html", {"stories": stories})


@login_required
def story_detail(request, pk):
    story = story_for_view(request, pk)
    return render(request, "genealogy/story_detail.html", {
        "story": story, "is_owner": can_edit(request.user, story.owner),
    })


@login_required
def story_create(request):
    owner = require_edit(request)
    initial = {}
    if request.GET.get("person"):
        initial["person"] = request.GET["person"]
    form = StoryForm(request.POST or None, owner=owner, initial=initial)
    if request.method == "POST" and form.is_valid():
        story = form.save(commit=False)
        story.owner = owner
        story.save()
        history.record(owner, request.user, Change.Action.CREATED, story.person, subject=story.title, what="story")
        messages.success(request, _("The story has been saved."))
        return redirect(story)
    return render(request, "genealogy/story_form.html", {"form": form, "is_new": True})


@login_required
def story_edit(request, pk):
    story = story_for_edit(request, pk)
    form = StoryForm(request.POST or None, instance=story, owner=story.owner)
    if request.method == "POST" and form.is_valid():
        form.save()
        history.record(story.owner, request.user, Change.Action.UPDATED, story.person, subject=story.title, what="story")
        messages.success(request, _("The story has been saved."))
        return redirect(story)
    return render(request, "genealogy/story_form.html", {"form": form, "story": story, "is_new": False})


@login_required
def story_delete(request, pk):
    story = story_for_edit(request, pk)
    if request.method == "POST":
        history.record(story.owner, request.user, Change.Action.DELETED, subject=story.title, what="story")
        story.delete()
        messages.success(request, _("The story has been deleted."))
        return redirect("genealogy:stories")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": story.title, "cancel_url": story.get_absolute_url(),
    })


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
def _ranked(queryset, query, limit):
    """People matching every word of `query`, best matches first.

    A match at the start of the first name ranks highest, then at the start
    of any name, then anywhere; ties are ordered by name.
    """
    tokens = search_tokens(query)
    if not tokens:
        return []
    found = list(_search(queryset, query)[:400])

    def score(p):
        words = p.search_key.split()
        sc = 0
        if words and words[0].startswith(tokens[0]):
            sc -= 4
        if all(any(w.startswith(t) for w in words) for t in tokens):
            sc -= 2
        return (sc, p.first_name.lower(), p.last_name.lower())

    return sorted(found, key=score)[:limit]


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        archive = Archive(request.archive)
        focus = _focus_for(request, archive)
        branches = archive.branches(focus) if focus else {}
        found = _ranked(Person.objects.filter(owner=request.archive), query, 120)
        results = [(p, archive.label(focus, p.pk) if focus else "", branches.get(p.pk, "other")) for p in found]
    template = "genealogy/_search_results.html" if request.GET.get("partial") else "genealogy/search.html"
    return render(request, template, {"query": query, "results": results})


@login_required
def search_json(request):
    """Live search for the command palette, the pickers and the tree."""
    owner = archive_owner(request, request.GET.get("owner"))
    query = request.GET.get("q", "").strip()
    archive = Archive(owner)
    focus = _focus_for(request, archive)
    branches = archive.branches(focus) if focus else {}
    people = Person.objects.filter(owner=owner)
    if request.GET.get("gender") in ("male", "female"):
        people = people.filter(gender=request.GET["gender"])
    found = _ranked(people, query, 8) if query else []
    return JsonResponse({"results": [{
        "id": p.pk, "name": p.short_name, "years": p.lifespan,
        "label": archive.label(focus, p.pk) if focus and p.pk != focus else "",
        "url": p.get_absolute_url(), "initials": p.initials, "gender": p.gender,
        "branch": branches.get(p.pk, "other"),
        "photo": p.photo.url if p.photo else "",
    } for p in found], "all_url": f"{reverse('genealogy:search')}?q={quote(query)}"})


@require_POST
@login_required
def set_self(request, pk):
    """"This is me": the viewer's own record in the archive they work in."""
    person = person_for_view(request, pk)
    if person.owner_id != request.archive.pk or hasattr(person, "account"):
        raise PermissionDenied(_("Access denied."))
    from apps.accounts.models import Membership

    request.user.person = person
    request.user.save(update_fields=["person"])
    if request.user.active_archive_id:
        Membership.objects.filter(owner=request.archive, member=request.user).update(person=person)
    messages.success(request, _("The information has been saved."))
    return redirect(person)


# ---------------------------------------------------------------------------
# Events and upcoming dates
# ---------------------------------------------------------------------------
@login_required
def upcoming(request):
    today = timezone.localdate()
    days = 120
    items = [(o, render_parts(o.kind, o.params, (o.date - today).days), (o.date - today).days)
             for o in occasions(request.archive, today, today + datetime.timedelta(days=days))]
    events = Event.objects.filter(owner=request.archive).prefetch_related("people")
    by_year = {}
    for e in events:
        by_year.setdefault(e.year, []).append(e)
    return render(request, "genealogy/events.html", {
        "items": items, "days": days, "by_year": sorted(by_year.items(), key=lambda kv: -(kv[0] or 0)),
        "kinds": Event.Kind.choices,
    })


@login_required
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.prefetch_related("people"), pk=pk)
    if not can_view(request.user, event.owner):
        raise PermissionDenied(_("Access denied."))
    return render(request, "genealogy/event_detail.html", {
        "event": event, "is_owner": can_edit(request.user, event.owner)})


def _own_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    require_edit(request, event.owner)
    return event


@login_required
def event_create(request):
    owner = require_edit(request)
    initial = {}
    if request.GET.get("kind") in dict(Event.Kind.choices):
        initial["kind"] = request.GET["kind"]
    if request.GET.get("person", "").isdigit():
        initial["people"] = [int(request.GET["person"])]
    form = EventForm(request.POST or None, owner=owner, initial=initial)
    if request.method == "POST" and form.is_valid():
        event = form.save()
        history.record(owner, request.user, Change.Action.CREATED, subject=event.display_title, what="event")
        messages.success(request, _("The event has been saved."))
        return redirect(event)
    return render(request, "genealogy/event_form.html", {"form": form, "is_new": True})


@login_required
def event_edit(request, pk):
    event = _own_event(request, pk)
    form = EventForm(request.POST or None, instance=event, owner=event.owner)
    if request.method == "POST" and form.is_valid():
        form.save()
        history.record(event.owner, request.user, Change.Action.UPDATED, subject=event.display_title, what="event")
        messages.success(request, _("The event has been saved."))
        return redirect(event)
    return render(request, "genealogy/event_form.html", {"form": form, "event": event, "is_new": False})


@login_required
def event_delete(request, pk):
    event = _own_event(request, pk)
    if request.method == "POST":
        history.record(event.owner, request.user, Change.Action.DELETED, subject=event.display_title, what="event")
        event.delete()
        messages.success(request, _("The event has been deleted."))
        return redirect("genealogy:upcoming")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": event.display_title, "cancel_url": event.get_absolute_url(),
    })


# ---------------------------------------------------------------------------
# "Who is who to whom?", GEDCOM and the archive file
# ---------------------------------------------------------------------------
@login_required
def calculator(request):
    archive = Archive(request.archive)
    a = b = None
    result = None
    try:
        a = int(request.GET.get("a") or viewer_person(request, archive) or 0)
        b = int(request.GET.get("b") or 0)
    except ValueError:
        a = b = None
    if a in archive.people and b in archive.people and a != b:
        chain = archive.path(a, b)
        steps = []
        if chain:
            for prev, cur in zip(chain, chain[1:]):
                steps.append((archive.people[cur], archive.label(prev, cur)))
        result = {
            "a": archive.people[a], "b": archive.people[b],
            "b_to_a": archive.label(a, b), "a_to_b": archive.label(b, a),
            "chain_start": archive.people[a], "steps": steps, "connected": chain is not None,
        }
    return render(request, "genealogy/calculator.html", {
        "a": a, "b": b, "result": result,
        "person_a": archive.people.get(a), "person_b": archive.people.get(b),
    })


@login_required
def gedcom_export(request):
    archive = Archive(request.archive)
    data = gedcom.export(archive, request.archive.display_name)
    response = HttpResponse(data.encode("utf-8"), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(True, pgettext("file name", "family-tree") + ".ged")
    return response


@require_POST
@login_required
def gedcom_import(request):
    """Add the people of a GEDCOM file (from another genealogy program) to the archive."""
    owner = require_edit(request)
    upload = request.FILES.get("file")
    if upload is None or upload.size > 8 * 1024 * 1024:
        messages.error(request, _("Choose a GEDCOM file (up to 8 MB)."))
        return redirect(reverse("accounts:data") + "#gedcom")
    raw = upload.read()
    try:
        counts = gedcom.import_file(owner, raw)
    except gedcom.GedcomError:
        messages.error(request, _("This file could not be read as GEDCOM."))
        return redirect(reverse("accounts:data") + "#gedcom")
    history.record(owner, request.user, Change.Action.CREATED, subject=upload.name[:200], what="gedcom",
                   details=counts)
    messages.success(request, _("Imported from GEDCOM: %(people)d people, %(families)d families.") % counts)
    return redirect("genealogy:duplicates" if duplicates.pairs(owner) else "genealogy:tree")


@login_required
def archive_export(request):
    """The signed-in user's own archive as one JSON file (with photos)."""
    data = archive_io.export_archive(request.user)
    response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=1), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(True, archive_io.export_filename())
    return response
