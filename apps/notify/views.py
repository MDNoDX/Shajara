from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from . import telegram
from .forms import NotificationSettingsForm
from .models import Notification, NotificationSettings


@login_required
def notification_list(request):
    items = list(request.user.notifications.all()[:100])
    return render(request, "notify/list.html", {"items": items})


@login_required
def notification_open(request, pk):
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    if not note.read_at:
        note.read_at = timezone.now()
        note.save(update_fields=["read_at"])
    target = note.url if url_has_allowed_host_and_scheme(note.url, {request.get_host()}) else ""
    return redirect(target or "notify:list")


@require_POST
@login_required
def mark_all_read(request):
    request.user.notifications.filter(read_at=None).update(read_at=timezone.now())
    return redirect(request.POST.get("next") or "notify:list")


@login_required
def notification_settings(request):
    prefs = NotificationSettings.for_user(request.user)
    form = NotificationSettingsForm(request.POST or None, instance=prefs)
    if request.method == "POST" and form.is_valid():
        form.save()
        prefs.last_generated = None  # re-check today's reminders with the new choices
        prefs.save(update_fields=["last_generated"])
        messages.success(request, _("The information has been saved."))
        return redirect("notify:settings")
    return render(request, "notify/settings.html", {
        "form": form, "prefs": prefs, "telegram_available": telegram.configured(),
    })


@require_POST
@login_required
def telegram_connect(request):
    prefs = NotificationSettings.for_user(request.user)
    url = telegram.link_url(prefs) if telegram.configured() else ""
    if not url:
        messages.error(request, _("Telegram reminders are not available at the moment."))
        return redirect("notify:settings")
    return redirect(url)


@require_POST
@login_required
def telegram_disconnect(request):
    prefs = NotificationSettings.for_user(request.user)
    prefs.telegram_enabled = False
    prefs.telegram_chat_id = None
    prefs.telegram_name = ""
    prefs.save(update_fields=["telegram_enabled", "telegram_chat_id", "telegram_name"])
    messages.info(request, _("Telegram has been disconnected."))
    return redirect("notify:settings")
