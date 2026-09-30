import datetime
from collections import deque

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
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
