"""Family stories."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from .. import history
from ..access import can_edit, require_edit, story_for_edit, story_for_view
from ..forms import StoryForm
from ..models import Change, Story


@login_required
def story_list(request):
    stories = Story.objects.filter(owner=request.archive).select_related("person")
    return render(request, "genealogy/stories/list.html", {"stories": stories})


@login_required
def story_detail(request, pk):
    story = story_for_view(request, pk)
    return render(request, "genealogy/stories/detail.html", {
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
    return render(request, "genealogy/stories/form.html", {"form": form, "is_new": True})


@login_required
def story_edit(request, pk):
    story = story_for_edit(request, pk)
    form = StoryForm(request.POST or None, instance=story, owner=story.owner)
    if request.method == "POST" and form.is_valid():
        form.save()
        history.record(story.owner, request.user, Change.Action.UPDATED, story.person, subject=story.title, what="story")
        messages.success(request, _("The story has been saved."))
        return redirect(story)
    return render(request, "genealogy/stories/form.html", {"form": form, "story": story, "is_new": False})


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
