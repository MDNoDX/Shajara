from django.conf import settings
from django.utils.translation import get_language

from apps.friends.services import incoming_requests

from .languages import CYRILLIC_SCRIPT, HTML_LANG, LANGUAGE_LABELS, LANGUAGE_SHORT, language_options, normalize_language


def site(request):
    current = normalize_language(get_language()) or settings.LANGUAGE_CODE
    context = {
        "current_language": current,
        "current_language_label": LANGUAGE_LABELS[current],
        "current_language_short": LANGUAGE_SHORT[current],
        "html_lang": HTML_LANG.get(current, "uz"),
        "is_cyrillic": current in CYRILLIC_SCRIPT,
        "language_options": language_options(current),
        "pending_requests": 0,
        "google_login": bool(settings.GOOGLE_CLIENT_ID),
    }
    user = getattr(request, "user", None)
    palette = request.COOKIES.get("palette", "atlas")
    if user is not None and user.is_authenticated:
        context["pending_requests"] = incoming_requests(user).count()
        palette = user.palette
    context["palette"] = palette if palette in ("atlas", "osmon", "bog", "anor") else "atlas"
    return context
