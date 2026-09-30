"""The family tree: the page, its data (tree and fan), the side sheet with quick add, PDFs and the book."""
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from apps.core.text import surname_from_name

from .. import pdf
from ..access import archive_owner, can_edit, person_for_edit, person_for_view, viewer_person
from ..kinship import Archive
from ..terminology import ADD_RELATION, BRANCHES
from ..tree import build_tree
from ._common import _focus_for, _pdf_response, _tree_state
from .people import _relative_form, _save_relative


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
