import datetime
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

from . import gedcom, pdf
from .access import archive_owner, can_view, person_for_edit, person_for_view, story_for_edit, story_for_view
from .forms import EventForm, MarriageForm, PersonForm, RelativeWithSpouseForm, StoryForm
from .kinship import Archive
from .models import Event, Marriage, Person, Story
from .terminology import ADD_RELATION, SECTION
from .tree import build_tree


def _focus_for(owner, archive, requested=None):
    if requested:
        try:
            pk = int(requested)
        except (TypeError, ValueError):
            pk = None
        if pk in archive.people:
            return pk
    if owner.person_id in archive.people:
        return owner.person_id
    return next(iter(archive.people), None)


def _ids(value):
    out = set()
    for part in (value or "").split(","):
        if part.strip().isdigit() and len(out) < 500:
            out.add(int(part))
    return out


def _tree_state(request):
    """Which branches are open: ?all=1&open=…&closed=…&folded=… (comma-separated ids)."""
    return {
        "open_all": request.GET.get("all") == "1",
        "opened": _ids(request.GET.get("open")),
        "closed": _ids(request.GET.get("closed")),
        "folded": _ids(request.GET.get("folded")),
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
@login_required
def people_list(request):
    query = request.GET.get("q", "").strip()
    archive = Archive(request.user)
    people = Person.objects.filter(owner=request.user)
    focus = _focus_for(request.user, archive)
    if query:
        people = _ranked(people, query, 500)
    rows = [(p, archive.label(focus, p.pk) if focus else "") for p in people]
    template = "genealogy/_people_grid.html" if request.GET.get("partial") else "genealogy/people_list.html"
    return render(request, template, {"rows": rows, "query": query, "total": len(archive.people)})


@login_required
def person_detail(request, pk):
    person = person_for_view(request, pk)
    archive = Archive(person.owner)
    is_owner = person.owner_id == request.user.pk
    me = request.user.person_id if is_owner else person.owner.person_id

    def people(pks):
        return [(archive.people[x], archive.label(person.pk, x)) for x in pks]

    context = {
        "person": person,
        "is_owner": is_owner,
        "relation_to_me": archive.label(me, person.pk) if me and me != person.pk else "",
        "father": archive.people.get(person.father_id),
        "mother": archive.people.get(person.mother_id),
        "spouses": people(archive.spouses(person.pk)),
        "marriages": [m for _sid, m in archive.unions.get(person.pk, [])],
        "children": people(archive.children.get(person.pk, [])),
        "siblings": people(archive.siblings(person.pk)),
        "stories": person.stories.all(),
        "events": person.events.all(),
        "friends": person.friends.all(),
        "muchal": person.muchal,
        "next_muchal": next_muchal_year(person.birth_year, person.birth_month, person.birth_day)
        if not person.is_deceased else None,
        "section": SECTION,
        "add_relation": ADD_RELATION,
        "is_me": is_owner and request.user.person_id == person.pk,
    }
    return render(request, "genealogy/person_detail.html", context)


@login_required
def person_create(request):
    form = PersonForm(request.POST or None, request.FILES or None, owner=request.user, archive=Archive(request.user))
    if request.method == "POST" and form.is_valid():
        person = form.save()
        messages.success(request, _("The person has been added to the family tree."))
        return redirect(person)
    return render(request, "genealogy/person_form.html", {"form": form, "is_new": True})


@login_required
def person_edit(request, pk):
    person = person_for_edit(request, pk)
    archive = Archive(request.user)
    form = PersonForm(request.POST or None, request.FILES or None, instance=person, owner=request.user, archive=archive)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("The information has been saved."))
        return redirect(person)
    return render(request, "genealogy/person_form.html", {"form": form, "person": person, "is_new": False})


@login_required
def person_delete(request, pk):
    person = person_for_edit(request, pk)
    if request.user.person_id == person.pk:
        messages.error(request, _("Your own record cannot be deleted."))
        return redirect(person)
    if request.method == "POST":
        person.delete()
        messages.success(request, _("The record has been deleted."))
        return redirect("genealogy:people")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": person.full_name, "cancel_url": person.get_absolute_url(),
    })


@login_required
def relative_add(request, pk):
    anchor = person_for_edit(request, pk)
    archive = Archive(request.user)
    spouses = [archive.people[s] for s in archive.spouses(anchor.pk)]
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
    form = RelativeWithSpouseForm(
        request.POST or None, request.FILES or None, owner=request.user, archive=archive,
        anchor=anchor, spouses=spouses, initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
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
    if marriage.owner_id != request.user.pk:
        raise PermissionDenied(_("You do not have permission to change this information."))
    back = request.GET.get("from") or marriage.husband_id
    form = MarriageForm(request.POST or None, instance=marriage)
    if request.method == "POST":
        if "delete" in request.POST:
            marriage.delete()
            messages.success(request, _("The marriage record has been deleted."))
            return redirect("genealogy:person", pk=back)
        if form.is_valid():
            form.save()
            messages.success(request, _("The information has been saved."))
            return redirect("genealogy:person", pk=back)
    return render(request, "genealogy/marriage_form.html", {"form": form, "marriage": marriage, "back": back})


@login_required
def person_pdf(request, pk):
    person = person_for_view(request, pk)
    archive = Archive(person.owner)
    data = pdf.person_pdf(archive, person, focus_id=person.owner.person_id, stories=list(person.stories.all()))
    return _pdf_response(data, f"{person.short_name}.pdf")


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------
@login_required
def tree_page(request, username=None):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(owner, archive, request.GET.get("person"))
    return render(request, "genealogy/tree.html", {
        "owner": owner,
        "is_owner": owner.pk == request.user.pk,
        "focus": archive.people.get(focus),
        "people": sorted(archive.people.values(), key=lambda p: p.full_name),
        "data_url": reverse("genealogy:tree_data_for", args=[owner.username]),
        "pdf_url": reverse("genealogy:tree_pdf_for", args=[owner.username]),
    })


@login_required
def tree_data(request, username):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(owner, archive, request.GET.get("person"))
    if focus is None:
        return JsonResponse({"nodes": [], "lines": [], "width": 0, "height": 0, "focus": None})
    return JsonResponse(build_tree(archive, focus, viewer_is_owner=owner.pk == request.user.pk, **_tree_state(request)))


@login_required
def tree_pdf(request, username):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(owner, archive, request.GET.get("person"))
    if focus is None:
        raise Http404(_("The family tree is empty."))
    layout = build_tree(archive, focus, photo_urls=False, viewer_is_owner=owner.pk == request.user.pk,
                        **_tree_state(request))
    person = archive.people[focus]
    subtitle = _("Centred on %(name)s. Relationship names are given as seen from this person.") % {
        "name": person.full_name}
    data = pdf.tree_pdf(layout, _("Family tree"), subtitle)
    return _pdf_response(data, pgettext("file name", "family-tree") + ".pdf")


@login_required
def family_book(request, username=None):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(owner, archive)
    if focus is None:
        raise Http404(_("The family tree is empty."))
    data = pdf.family_book_pdf(archive, focus, owner.display_name, viewer_is_owner=owner.pk == request.user.pk)
    return _pdf_response(data, pgettext("file name", "family-book") + ".pdf")


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------
@login_required
def story_list(request):
    stories = Story.objects.filter(owner=request.user).select_related("person")
    return render(request, "genealogy/story_list.html", {"stories": stories})


@login_required
def story_detail(request, pk):
    story = story_for_view(request, pk)
    return render(request, "genealogy/story_detail.html", {
        "story": story, "is_owner": story.owner_id == request.user.pk,
    })


@login_required
def story_create(request):
    initial = {}
    if request.GET.get("person"):
        initial["person"] = request.GET["person"]
    form = StoryForm(request.POST or None, owner=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        story = form.save(commit=False)
        story.owner = request.user
        story.save()
        messages.success(request, _("The story has been saved."))
        return redirect(story)
    return render(request, "genealogy/story_form.html", {"form": form, "is_new": True})


@login_required
def story_edit(request, pk):
    story = story_for_edit(request, pk)
    form = StoryForm(request.POST or None, instance=story, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("The story has been saved."))
        return redirect(story)
    return render(request, "genealogy/story_form.html", {"form": form, "story": story, "is_new": False})


@login_required
def story_delete(request, pk):
    story = story_for_edit(request, pk)
    if request.method == "POST":
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
        s = 0
        if words and words[0].startswith(tokens[0]):
            s -= 4
        if all(any(w.startswith(t) for w in words) for t in tokens):
            s -= 2
        return (s, p.first_name.lower(), p.last_name.lower())

    return sorted(found, key=score)[:limit]


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        archive = Archive(request.user)
        focus = _focus_for(request.user, archive)
        found = _ranked(Person.objects.filter(owner=request.user), query, 120)
        results = [(p, archive.label(focus, p.pk) if focus else "") for p in found]
    template = "genealogy/_search_results.html" if request.GET.get("partial") else "genealogy/search.html"
    return render(request, template, {"query": query, "results": results})


@login_required
def search_json(request):
    """Live search for the header box and the tree's person picker."""
    owner = archive_owner(request, request.GET.get("owner"))
    query = request.GET.get("q", "").strip()
    archive = Archive(owner)
    focus = _focus_for(owner, archive)
    found = _ranked(Person.objects.filter(owner=owner), query, 8) if query else []
    return JsonResponse({"results": [{
        "id": p.pk, "name": p.full_name, "years": p.lifespan,
        "label": archive.label(focus, p.pk) if focus and p.pk != focus else "",
        "url": p.get_absolute_url(), "initials": p.initials, "gender": p.gender,
        "photo": p.photo.url if p.photo else "",
    } for p in found], "all_url": f"{reverse('genealogy:search')}?q={quote(query)}"})


@require_POST
@login_required
def set_self(request, pk):
    person = person_for_edit(request, pk)
    request.user.person = person
    request.user.save(update_fields=["person"])
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
             for o in occasions(request.user, today, today + datetime.timedelta(days=days))]
    events = Event.objects.filter(owner=request.user).prefetch_related("people")
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
    return render(request, "genealogy/event_detail.html", {"event": event, "is_owner": event.owner_id == request.user.pk})


def _own_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.owner_id != request.user.pk:
        raise PermissionDenied(_("You do not have permission to change this information."))
    return event


@login_required
def event_create(request):
    initial = {}
    if request.GET.get("kind") in dict(Event.Kind.choices):
        initial["kind"] = request.GET["kind"]
    if request.GET.get("person", "").isdigit():
        initial["people"] = [int(request.GET["person"])]
    form = EventForm(request.POST or None, owner=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        event = form.save()
        messages.success(request, _("The event has been saved."))
        return redirect(event)
    return render(request, "genealogy/event_form.html", {"form": form, "is_new": True})


@login_required
def event_edit(request, pk):
    event = _own_event(request, pk)
    form = EventForm(request.POST or None, instance=event, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("The event has been saved."))
        return redirect(event)
    return render(request, "genealogy/event_form.html", {"form": form, "event": event, "is_new": False})


@login_required
def event_delete(request, pk):
    event = _own_event(request, pk)
    if request.method == "POST":
        event.delete()
        messages.success(request, _("The event has been deleted."))
        return redirect("genealogy:upcoming")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": event.display_title, "cancel_url": event.get_absolute_url(),
    })


# ---------------------------------------------------------------------------
# "Who is who to whom?" and GEDCOM
# ---------------------------------------------------------------------------
@login_required
def calculator(request):
    archive = Archive(request.user)
    people = sorted(archive.people.values(), key=lambda p: p.full_name)
    a = b = None
    result = None
    try:
        a = int(request.GET.get("a") or request.user.person_id or 0)
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
    return render(request, "genealogy/calculator.html", {"people": people, "a": a, "b": b, "result": result})


@login_required
def gedcom_export(request):
    archive = Archive(request.user)
    data = gedcom.export(archive, request.user.display_name)
    response = HttpResponse(data.encode("utf-8"), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(True, pgettext("file name", "family-tree") + ".ged")
    return response
