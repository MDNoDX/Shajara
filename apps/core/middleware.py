from django.conf import settings
from django.utils import timezone, translation

from .languages import EXPLICIT_ONLY, normalize_language
from .timezones import zone


class UserLanguageMiddleware:
    """Language and time zone for each request.

    Runs after LocaleMiddleware (cookie / Accept-Language / default) and
    AuthenticationMiddleware:
    * signed-in users get the language and time zone saved on their account,
      and the language cookie is kept in step so the choice survives signing out;
    * guests are switched to Russian or English only by choosing it (cookie),
      not by their browser language: the site opens in Uzbek.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        signed_in = user is not None and user.is_authenticated
        if signed_in:
            preferred = normalize_language(user.preferred_language)
            if preferred:
                translation.activate(preferred)
                request.LANGUAGE_CODE = preferred
            timezone.activate(zone(user.time_zone))
        else:
            chosen = normalize_language(request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME))
            if not chosen and translation.get_language() in EXPLICIT_ONLY:
                translation.activate(settings.LANGUAGE_CODE)
                request.LANGUAGE_CODE = settings.LANGUAGE_CODE

        response = self.get_response(request)
        timezone.deactivate()

        if signed_in:
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
