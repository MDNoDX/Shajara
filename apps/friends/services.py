from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import FriendRequest


def between(a, b):
    return FriendRequest.objects.filter(Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a))


def are_friends(a, b):
    if not a.is_authenticated or not b:
        return False
    return between(a, b).filter(status=FriendRequest.Status.ACCEPTED).exists()


def friends_of(user):
    accepted = FriendRequest.objects.filter(status=FriendRequest.Status.ACCEPTED)
    ids = set(accepted.filter(from_user=user).values_list("to_user", flat=True))
    ids |= set(accepted.filter(to_user=user).values_list("from_user", flat=True))
    return get_user_model().objects.filter(pk__in=ids).order_by("first_name", "last_name", "username")


def incoming_requests(user):
    return FriendRequest.objects.filter(to_user=user, status=FriendRequest.Status.PENDING).select_related("from_user")


def outgoing_requests(user):
    return FriendRequest.objects.filter(from_user=user, status=FriendRequest.Status.PENDING).select_related("to_user")


def friendship_state(viewer, other):
    """One of: self, friends, sent, received, none."""
    if viewer.pk == other.pk:
        return "self"
    req = between(viewer, other).first()
    if not req or req.status == FriendRequest.Status.DECLINED:
        return "none"
    if req.status == FriendRequest.Status.ACCEPTED:
        return "friends"
    return "sent" if req.from_user_id == viewer.pk else "received"
