"""Who may see and change a family archive.

The owner may change everything. Accepted friends may look at the owner's
tree, people and stories but not change them.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext as _

from apps.friends.services import are_friends

from .models import Person, Story


def can_view(viewer, owner):
    return viewer.is_authenticated and (viewer.pk == owner.pk or are_friends(viewer, owner))


def person_for_view(request, pk):
    person = Person.objects.select_related("owner", "father", "mother").filter(pk=pk).first()
    if person is None:
        raise Http404(_("Person not found."))
    if not can_view(request.user, person.owner):
        raise PermissionDenied(_("Access denied."))
    return person


def person_for_edit(request, pk):
    person = person_for_view(request, pk)
    if person.owner_id != request.user.pk:
        raise PermissionDenied(_("You do not have permission to change this information."))
    return person


def story_for_view(request, pk):
    story = Story.objects.select_related("owner", "person").filter(pk=pk).first()
    if story is None:
        raise Http404(_("Story not found."))
    if not can_view(request.user, story.owner):
        raise PermissionDenied(_("Access denied."))
    return story


def story_for_edit(request, pk):
    story = story_for_view(request, pk)
    if story.owner_id != request.user.pk:
        raise PermissionDenied(_("You do not have permission to change this information."))
    return story


def archive_owner(request, username=None):
    """The user whose archive is being viewed: the viewer, or a friend."""
    if not username or username == request.user.username:
        return request.user
    owner = get_user_model().objects.filter(username=username).first()
    if owner is None:
        raise Http404(_("User not found."))
    if not can_view(request.user, owner):
        raise PermissionDenied(_("Access denied."))
    return owner
