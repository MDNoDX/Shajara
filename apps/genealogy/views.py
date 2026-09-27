from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from apps.core.text import search_tokens

from . import pdf
from .access import archive_owner, person_for_edit, person_for_view, story_for_edit, story_for_view
from .forms import MarriageForm, PersonForm, RelativeWithSpouseForm, StoryForm
from .kinship import Archive
from .models import Marriage, Person, Story
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
    if query:
        people = _search(people, query)
    focus = _focus_for(request.user, archive)
    rows = [(p, archive.label(focus, p.pk) if focus else "") for p in people]
    return render(request, "genealogy/people_list.html", {
        "rows": rows, "query": query, "total": len(archive.people),
    })


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
        if relation in ("child", "sibling"):
            initial["last_name"] = anchor.last_name if anchor.is_male or relation == "sibling" else ""
    form = RelativeWithSpouseForm(
        request.POST or None, request.FILES or None, owner=request.user, archive=archive,
        anchor=anchor, spouses=spouses, initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("The person has been added to the family tree."))
        return redirect(anchor)
    return render(request, "genealogy/relative_form.html", {"form": form, "anchor": anchor, "has_spouses": bool(spouses)})


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
    return JsonResponse(build_tree(archive, focus, viewer_is_owner=owner.pk == request.user.pk))


@login_required
def tree_pdf(request, username):
    owner = archive_owner(request, username)
    archive = Archive(owner)
    focus = _focus_for(owner, archive, request.GET.get("person"))
    if focus is None:
        raise Http404(_("The family tree is empty."))
    layout = build_tree(archive, focus, photo_urls=False, viewer_is_owner=owner.pk == request.user.pk)
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
@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        archive = Archive(request.user)
        focus = _focus_for(request.user, archive)
        found = _search(Person.objects.filter(owner=request.user), query)[:100]
        results = [(p, archive.label(focus, p.pk) if focus else "") for p in found]
    return render(request, "genealogy/search.html", {"query": query, "results": results})


@require_POST
@login_required
def set_self(request, pk):
    person = person_for_edit(request, pk)
    request.user.person = person
    request.user.save(update_fields=["person"])
    messages.success(request, _("The information has been saved."))
    return redirect(person)

