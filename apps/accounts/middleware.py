from django.shortcuts import redirect
from django.urls import reverse

# Paths a user without a profile may still open.
ALLOWED_PREFIXES = ("/profilni-toldirish/", "/chiqish/", "/til/", "/jsi18n/", "/static/", "/media/",
                    "/accounts/", "/admin/", "/salomatlik/", "/cron/", "/telegram/", "/ilova/")


class ProfileCompletionMiddleware:
    """A user without a record in the tree (e.g. just signed up with Google)
    is asked for the few details the tree needs before anything else."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (user is not None and user.is_authenticated and not user.person_id and not user.is_staff
                and not request.path.startswith(ALLOWED_PREFIXES)):
            return redirect(f"{reverse('accounts:complete_profile')}?next={request.get_full_path()}")
        return self.get_response(request)
