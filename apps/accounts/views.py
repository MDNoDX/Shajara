from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language
from apps.friends.services import incoming_requests

from .forms import (
    CompleteProfileForm,
    LanguageForm,
    LoginForm,
    PaletteForm,
    PasswordChangeForm,
    PasswordResetForm,
    ProfileForm,
    RegisterForm,
    SetPasswordForm,
)


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, _("Welcome! Your account has been created."))
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        # Switch to the account's language straight away.
        lang = normalize_language(form.get_user().preferred_language)
        if lang:
            translation.activate(lang)
        return response


@login_required
def profile(request):
    user = request.user
    return render(request, "accounts/profile.html", {
        "people_count": user.people.count(),
        "friends_count": user.contacts.count(),
        "stories_count": user.stories.count(),
        "incoming": incoming_requests(user),
    })


@login_required
def settings_view(request):
    user = request.user
    profile_form = ProfileForm(instance=user, prefix="profile")
    language_form = LanguageForm(initial={"language": user.preferred_language}, prefix="lang")
    palette_form = PaletteForm(instance=user, prefix="pal")
    if request.method == "POST":
        if "save_palette" in request.POST:
            palette_form = PaletteForm(request.POST, instance=user, prefix="pal")
            if palette_form.is_valid():
                palette_form.save()
                messages.success(request, _("The information has been saved."))
                return redirect("accounts:settings")
        if "save_profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=user, prefix="profile")
            if profile_form.is_valid():
                profile_form.save()
                if user.person:
                    user.person.first_name = user.first_name
                    user.person.last_name = user.last_name
                    if user.gender:
                        user.person.gender = user.gender
                    user.person.save()
                messages.success(request, _("The information has been saved."))
                return redirect("accounts:settings")
        elif "save_language" in request.POST:
            language_form = LanguageForm(request.POST, prefix="lang")
            if language_form.is_valid():
                user.preferred_language = language_form.cleaned_data["language"]
                user.save(update_fields=["preferred_language"])
                translation.activate(user.preferred_language)
                messages.success(request, _("The interface language has been changed."))
                return redirect("accounts:settings")
    return render(request, "accounts/settings.html", {
        "profile_form": profile_form, "language_form": language_form, "palette_form": palette_form,
    })


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, _("Your password has been changed."))
        return redirect("accounts:settings")
    return render(request, "accounts/password_change.html", {"form": form})


password_reset = auth_views.PasswordResetView.as_view(
    form_class=PasswordResetForm,
    template_name="accounts/password_reset.html",
    email_template_name="registration/password_reset_email.txt",
    subject_template_name="registration/password_reset_subject.txt",
    success_url=reverse_lazy("accounts:password_reset_done"),
)
password_reset_done = auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html")
password_reset_confirm = auth_views.PasswordResetConfirmView.as_view(
    form_class=SetPasswordForm,
    template_name="accounts/password_reset_confirm.html",
    success_url=reverse_lazy("accounts:password_reset_complete"),
)
password_reset_complete = auth_views.PasswordResetCompleteView.as_view(
    template_name="accounts/password_reset_complete.html"
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
        target = request.GET.get("next") or ""
        if not url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
            target = ""
        return redirect(target or "home")
    return render(request, "accounts/complete_profile.html", {"form": form})


@login_required
def delete_account(request):
    """Delete the account and the whole family archive, after typing the username."""
    error = ""
    if request.method == "POST":
        if request.POST.get("confirm", "").strip() == request.user.username:
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, _("Your account and all its data have been deleted."))
            return redirect("home")
        error = _("The username does not match.")
    return render(request, "accounts/delete_account.html", {"error": error})
