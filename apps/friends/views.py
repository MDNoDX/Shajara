import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.text import search_tokens

from apps.genealogy.models import Person
from apps.notify.messages import render_parts
from apps.notify.occasions import occasions

from .forms import ContactForm
from .models import Contact, FriendRequest
from .services import between, friends_of, friendship_state, incoming_requests, outgoing_requests

User = get_user_model()


@login_required
def sharing(request):
    query = request.GET.get("q", "").strip()
    found = []
    if query:
        users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
        for token in search_tokens(query):
            users = users.filter(search_key__contains=token)
        found = [(u, friendship_state(request.user, u)) for u in users.order_by("first_name")[:30]]
    return render(request, "friends/sharing.html", {
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
        return redirect("friends:sharing")
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
    return redirect(request.POST.get("next") or "friends:sharing")


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
    return redirect("friends:sharing")


@require_POST
@login_required
def cancel_request(request, pk):
    req = get_object_or_404(FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.Status.PENDING)
    req.delete()
    messages.info(request, _("The request has been cancelled."))
    return redirect("friends:sharing")


@require_POST
@login_required
def remove_friend(request, user_id):
    other = get_object_or_404(User, pk=user_id)
    between(request.user, other).filter(status=FriendRequest.Status.ACCEPTED).delete()
    messages.info(request, _("Removed from your friends."))
    return redirect("friends:sharing")


# ---------------------------------------------------------------------------
# Friends of people in the tree (no account needed)
# ---------------------------------------------------------------------------
@login_required
def friends_list(request):
    contacts = Contact.objects.filter(owner=request.user).select_related("person")
    whose = request.GET.get("kimning", "")
    query = request.GET.get("q", "").strip()
    if whose.isdigit():
        contacts = contacts.filter(person_id=int(whose))
    for token in search_tokens(query):
        contacts = contacts.filter(search_key__contains=token)
    groups = {}
    for c in contacts.order_by("person__first_name", "name"):
        groups.setdefault(c.person, []).append(c)
    # The user's own friends first.
    ordered = sorted(groups.items(), key=lambda kv: (kv[0].pk != request.user.person_id, kv[0].first_name))
    people_with_friends = Person.objects.filter(owner=request.user, friends__isnull=False).distinct()
    today = timezone.localdate()
    upcoming = [o for o in occasions(request.user, today, today + datetime.timedelta(days=45))
                if o.kind == "friend_birthday"]
    return render(request, "friends/list.html", {
        "groups": ordered, "whose": whose, "query": query, "total": Contact.objects.filter(owner=request.user).count(),
        "people_with_friends": people_with_friends,
        "upcoming": [(o, render_parts(o.kind, o.params, (o.date - today).days)) for o in upcoming],
        "pending_requests_count": incoming_requests(request.user).count(),
    })


@login_required
def contact_create(request):
    initial = {}
    if request.GET.get("kimning", "").isdigit():
        initial["person"] = int(request.GET["kimning"])
    form = ContactForm(request.POST or None, owner=request.user, initial=initial)
    if request.method == "POST" and form.is_valid():
        contact = form.save()
        messages.success(request, _("The friend has been added."))
        return redirect(f"{reverse('friends:list')}?kimning={contact.person_id}")
    return render(request, "friends/contact_form.html", {"form": form, "is_new": True})


@login_required
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user)
    form = ContactForm(request.POST or None, instance=contact, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("The information has been saved."))
        return redirect("friends:list")
    return render(request, "friends/contact_form.html", {"form": form, "contact": contact, "is_new": False})


@login_required
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk, owner=request.user)
    if request.method == "POST":
        contact.delete()
        messages.success(request, _("The record has been deleted."))
        return redirect("friends:list")
    return render(request, "genealogy/confirm_delete.html", {
        "object_name": contact.name, "cancel_url": reverse("friends:list"),
    })
