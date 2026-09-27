from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.text import search_tokens

from .models import FriendRequest
from .services import between, friends_of, friendship_state, incoming_requests, outgoing_requests

User = get_user_model()


@login_required
def friends_list(request):
    query = request.GET.get("q", "").strip()
    found = []
    if query:
        users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
        for token in search_tokens(query):
            users = users.filter(search_key__contains=token)
        found = [(u, friendship_state(request.user, u)) for u in users.order_by("first_name")[:30]]
    return render(request, "friends/friends.html", {
        "friends": friends_of(request.user),
        "incoming": incoming_requests(request.user),
        "outgoing": outgoing_requests(request.user),
        "query": query,
        "found": found,
    })


@require_POST
@login_required
def send_request(request, user_id):
    other = get_object_or_404(User, pk=user_id, is_active=True)
    if other.pk == request.user.pk:
        return redirect("friends:list")
    existing = between(request.user, other).first()
    if existing is None:
        FriendRequest.objects.create(from_user=request.user, to_user=other)
        messages.success(request, _("Your friend request has been sent."))
    elif existing.status == FriendRequest.Status.DECLINED:
        existing.delete()
        FriendRequest.objects.create(from_user=request.user, to_user=other)
        messages.success(request, _("Your friend request has been sent."))
    elif existing.status == FriendRequest.Status.PENDING and existing.to_user_id == request.user.pk:
        _accept(existing)
        messages.success(request, _("You are now friends."))
    else:
        messages.info(request, _("A request has already been sent."))
    return redirect(request.POST.get("next") or "friends:list")


def _accept(req):
    req.status = FriendRequest.Status.ACCEPTED
    req.responded_at = timezone.now()
    req.save(update_fields=["status", "responded_at"])


@require_POST
@login_required
def answer_request(request, pk):
    req = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=FriendRequest.Status.PENDING)
    if request.POST.get("answer") == "accept":
        _accept(req)
        messages.success(request, _("You are now friends."))
    else:
        req.status = FriendRequest.Status.DECLINED
        req.responded_at = timezone.now()
        req.save(update_fields=["status", "responded_at"])
        messages.info(request, _("The request has been declined."))
    return redirect("friends:list")


@require_POST
@login_required
def cancel_request(request, pk):
    req = get_object_or_404(FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.Status.PENDING)
    req.delete()
    messages.info(request, _("The request has been cancelled."))
    return redirect("friends:list")


@require_POST
@login_required
def remove_friend(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    between(request.user, other).filter(status=FriendRequest.Status.ACCEPTED).delete()
    messages.info(request, _("Removed from your friends."))
    return redirect("friends:list")
