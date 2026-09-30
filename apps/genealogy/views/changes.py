"""Keeping the archive clean: possible duplicates, merging, the history of changes and undo."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .. import duplicates, history
from ..access import require_edit
from ..kinship import Archive
from ..models import Change, Person
from ._common import _focus_for


@login_required
def duplicates_page(request):
    owner = require_edit(request)
    archive = Archive(owner)
    focus = _focus_for(request, archive)
    pairs = [[(p, archive.label(focus, p.pk) if focus else "") for p in pair] for pair in duplicates.pairs(owner)]
    return render(request, "genealogy/changes/duplicates.html", {"pairs": pairs})


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
    return render(request, "genealogy/changes/history.html", {"rows": rows, "can_undo": request.can_edit})


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
