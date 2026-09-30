import datetime
from collections import deque

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone, translation
from django.utils.http import content_disposition_header, url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.muchal import current_cycle_year, muchal
from apps.friends.services import incoming_requests
from apps.genealogy.kinship import Archive
from apps.notify.messages import render_parts
from apps.notify.occasions import occasions

from .languages import normalize_language


def home(request):
    if not request.user.is_authenticated:
        return render(request, "core/landing.html")
    user = request.user
    archive = Archive(user)
    focus = user.person_id if user.person_id in archive.people else None
    recent = sorted(archive.people.values(), key=lambda p: p.updated_at, reverse=True)[:6]
    today = timezone.localdate()
    soon = [(o, render_parts(o.kind, o.params, (o.date - today).days), (o.date - today).days)
            for o in occasions(user, today, today + datetime.timedelta(days=30))][:8]
    generations = len({g for g in _generations(archive, focus).values()}) if focus else 0
    return render(request, "core/dashboard.html", {
        "people_count": len(archive.people),
        "friends_count": user.contacts.count(),
        "events_count": user.events.count(),
        "stories_count": user.stories.count(),
        "generations": generations,
        "recent": [(p, archive.label(focus, p.pk) if focus else "") for p in recent],
        "incoming": incoming_requests(user)[:5],
        "me": archive.people.get(focus),
        "soon": soon,
        "cycle_animal": muchal(current_cycle_year(), 6, 1),
    })


def _generations(archive, focus):
    """Generation number of everyone connected to `focus` (parents −1)."""
    gen = {focus: 0}
    queue = deque([focus])
    while queue:
        cur = queue.popleft()
        steps = [(p, -1) for p in archive.parents(cur)] + [(c, 1) for c in archive.children.get(cur, [])]
        steps += [(s, 0) for s in archive.spouses(cur)]
        for nxt, d in steps:
            if nxt not in gen:
                gen[nxt] = gen[cur] + d
                queue.append(nxt)
    return gen


@require_POST
def set_language(request):
    """Switch the interface language; saved on the account when signed in."""
    code = normalize_language(request.POST.get("language"))
    next_url = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        next_url = "/"
    response = redirect(next_url)
    if not code:
        return response
    if request.user.is_authenticated and request.user.preferred_language != code:
        request.user.preferred_language = code
        request.user.save(update_fields=["preferred_language"])
    translation.activate(code)
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME, code, max_age=settings.LANGUAGE_COOKIE_AGE, samesite="Lax",
        secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
    )
    return response


def media(request, name):
    """Serve a file from the database storage (photos)."""
    from django.http import Http404, HttpResponse
    from django.utils.http import http_date

    from .models import StoredFile

    obj = StoredFile.objects.filter(name=name).first()
    if obj is None:
        raise Http404
    response = HttpResponse(bytes(obj.content), content_type=obj.content_type)
    response["Cache-Control"] = "public, max-age=31536000, immutable"  # names are unique (uuid)
    response["Last-Modified"] = http_date(obj.created_at.timestamp())
    response["X-Content-Type-Options"] = "nosniff"
    return response


def health(request):
    """For the load balancer / container health check."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


def csrf_failure(request, reason=""):
    return render(request, "403_csrf.html", status=403)


def bad_request(request, exception=None):
    return render(request, "400.html", status=400)


def permission_denied(request, exception=None):
    message = str(exception) if exception and str(exception) else ""
    return render(request, "403.html", {"message": message}, status=403)


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


# ---------------------------------------------------------------------------
# Site administration (superusers only)
# ---------------------------------------------------------------------------
def _superuser(user):
    return user.is_active and user.is_superuser


@user_passes_test(_superuser)
def control_panel(request):
    from django.contrib.auth import get_user_model
    from django.db.models import Sum

    from apps.friends.models import Contact
    from apps.genealogy.models import Event, Person, Story
    from apps.notify import telegram
    from apps.notify.models import Notification, NotificationSettings

    from .models import StoredFile

    webhook = None
    if telegram.configured():
        try:
            webhook = telegram.call("getWebhookInfo", http_timeout=8)
        except telegram.TelegramError as exc:
            webhook = {"error": str(exc)}
    users = get_user_model().objects
    return render(request, "core/control_panel.html", {
        "stats": [
            (_("Users"), users.count()),
            (_("People in all trees"), Person.objects.count()),
            (_("Events"), Event.objects.count()),
            (_("Stories"), Story.objects.count()),
            (_("Friends"), Contact.objects.count()),
            (_("Photos"), StoredFile.objects.count()),
            (_("Notifications"), Notification.objects.count()),
            (_("Telegram connected"), NotificationSettings.objects.filter(telegram_enabled=True).count()),
        ],
        "photo_mb": round((StoredFile.objects.aggregate(s=Sum("size"))["s"] or 0) / 1024 / 1024, 1),
        "recent_users": users.order_by("-date_joined")[:10],
        "telegram": telegram.configured(), "webhook": webhook, "cron": bool(settings.CRON_SECRET),
        "google": bool(settings.GOOGLE_CLIENT_ID), "site_url": settings.SITE_URL,
    })


@user_passes_test(_superuser)
def full_backup(request):
    """The whole database as JSON (for `manage.py loaddata` on any server)."""
    import io

    from django.core.management import call_command

    buf = io.StringIO()
    call_command("dumpdata", "--natural-foreign", "--natural-primary", "--exclude=contenttypes",
                 "--exclude=auth.permission", "--exclude=admin.logentry", "--exclude=sessions", stdout=buf)
    response = HttpResponse(buf.getvalue(), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(
        True, f"shajara-full-backup-{timezone.localdate().isoformat()}.json")
    return response


@require_POST
@user_passes_test(_superuser)
def set_telegram_webhook(request):
    from django.contrib import messages
    from django.urls import reverse

    from apps.notify import telegram

    try:
        telegram.set_webhook(settings.SITE_URL + reverse("notify:telegram_webhook"))
        messages.success(request, _("The Telegram bot is connected to the site."))
    except telegram.TelegramError as exc:
        messages.error(request, str(exc))
    return redirect("control_panel")
