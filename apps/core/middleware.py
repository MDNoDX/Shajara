from django.conf import settings
from django.utils import translation

from .languages import normalize_language


class UserLanguageMiddleware:
    """Signed-in users see the language saved on their account.

    Runs after LocaleMiddleware (cookie / Accept-Language / default) and
    AuthenticationMiddleware. The language cookie is kept in step with the
    account so the choice also survives signing out.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        preferred = None
        if user is not None and user.is_authenticated:
            preferred = normalize_language(user.preferred_language)
            if preferred:
                translation.activate(preferred)
                request.LANGUAGE_CODE = preferred

        response = self.get_response(request)

        if user is not None and user.is_authenticated:
            preferred = normalize_language(user.preferred_language)
            if preferred and request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) != preferred:
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    preferred,
                    max_age=settings.LANGUAGE_COOKIE_AGE,
                    samesite="Lax",
                    secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
                )
        return response
