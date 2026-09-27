from django.conf import settings
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.friends.services import friends_of, incoming_requests
from apps.genealogy.kinship import Archive

from .languages import normalize_language


def home(request):
    if not request.user.is_authenticated:
        return render(request, "core/landing.html")
    user = request.user
    archive = Archive(user)
    focus = user.person_id if user.person_id in archive.people else None
    recent = sorted(archive.people.values(), key=lambda p: p.updated_at, reverse=True)[:6]
    return render(request, "core/dashboard.html", {
        "people_count": len(archive.people),
        "friends_count": friends_of(user).count(),
        "stories_count": user.stories.count(),
        "recent": [(p, archive.label(focus, p.pk) if focus else "") for p in recent],
        "incoming": incoming_requests(user)[:5],
        "me": archive.people.get(focus),
    })


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
