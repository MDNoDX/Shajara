from .service import ensure_today


class DailyRemindersMiddleware:
    """Creates the day's reminders on a user's first visit of the day, so the
    bell works even where no background worker runs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and request.method == "GET":
            ensure_today(user)
        return self.get_response(request)
