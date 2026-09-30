"""Getting in: sign up, sign in (with the second step), password reset, finishing a new profile."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language

from ..forms import CompleteProfileForm, LoginForm, PasswordResetForm, RegisterForm, SetPasswordForm


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, _("Welcome! Your account has been created."))
        return redirect(_after_sign_in(request))
    return render(request, "accounts/auth/register.html", {"form": form, "next": request.GET.get("next", "")})


def _after_sign_in(request, default="home"):
    """Where to go after signing in or up: a safe ?next, else an invite that
    was opened before, else the home page."""
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    token = request.session.get("invite")
    if token:
        return reverse("accounts:invite", args=[token])
    return default


class LoginView(auth_views.LoginView):
    template_name = "accounts/auth/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        token = self.request.session.get("invite")
        return reverse("accounts:invite", args=[token]) if token else super().get_default_redirect_url()

    def form_valid(self, form):
        user = form.get_user()
        if user.totp_enabled:
            # Second step: the password was right, now the code from the app.
            self.request.session["2fa_user"] = user.pk
            self.request.session["2fa_next"] = self.get_success_url()
            return redirect("accounts:two_factor")
        response = super().form_valid(form)
        # Switch to the account's language straight away.
        lang = normalize_language(user.preferred_language)
        if lang:
            translation.activate(lang)
        return response


def two_factor(request):
    """Second step of signing in: a code from the authenticator app, or a recovery code."""
    from django.contrib.auth import get_user_model
    from django.core.cache import cache

    from .. import totp
    from ..forms import CodeForm

    user = get_user_model().objects.filter(pk=request.session.get("2fa_user"), is_active=True).first()
    if user is None:
        return redirect("accounts:login")
    form = CodeForm(request.POST or None)
    key = f"2fa-fail:{user.pk}"
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        if cache.get(key, 0) >= 8:
            form.add_error("code", _("Too many attempts. Please try again in 15 minutes."))
        elif totp.verify(user.totp_secret, code) or totp.use_recovery_code(user, code):
            cache.delete(key)
            target = request.session.pop("2fa_next", "") or "home"
            request.session.pop("2fa_user", None)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect(target)
        else:
            cache.set(key, cache.get(key, 0) + 1, 15 * 60)
            form.add_error("code", _("The code is not correct."))
    return render(request, "accounts/auth/two_factor.html", {"form": form})


password_reset = auth_views.PasswordResetView.as_view(
    form_class=PasswordResetForm,
    template_name="accounts/auth/password_reset.html",
    email_template_name="registration/password_reset_email.txt",
    subject_template_name="registration/password_reset_subject.txt",
    success_url=reverse_lazy("accounts:password_reset_done"),
)
password_reset_done = auth_views.PasswordResetDoneView.as_view(template_name="accounts/auth/password_reset_done.html")
password_reset_confirm = auth_views.PasswordResetConfirmView.as_view(
    form_class=SetPasswordForm,
    template_name="accounts/auth/password_reset_confirm.html",
    success_url=reverse_lazy("accounts:password_reset_complete"),
)
password_reset_complete = auth_views.PasswordResetCompleteView.as_view(
    template_name="accounts/auth/password_reset_complete.html"
)


@login_required
def complete_profile(request):
    if request.user.person_id:
        return redirect("home")
    form = CompleteProfileForm(request.POST or None, initial={
        "first_name": request.user.first_name, "last_name": request.user.last_name,
    })
    if request.method == "POST" and form.is_valid():
        form.save(request.user)
        messages.success(request, _("Welcome! Your account has been created."))
        return redirect(_after_sign_in(request))
    return render(request, "accounts/auth/complete_profile.html", {"form": form})
