from django.conf import settings
from django.utils.translation import get_language

from apps.friends.services import incoming_requests

from .languages import CYRILLIC, HTML_LANG, LANGUAGE_LABELS, normalize_language, supported_codes


def site(request):
    current = normalize_language(get_language()) or "uz"
    context = {
        "current_language": current,
        "html_lang": HTML_LANG.get(current, "uz"),
        "is_cyrillic": current == CYRILLIC,
        "language_options": [
            {"code": code, "label": LANGUAGE_LABELS[code], "html_lang": HTML_LANG[code], "active": code == current}
            for code in supported_codes()
        ],
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
