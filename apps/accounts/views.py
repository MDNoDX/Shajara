from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language
from apps.friends.services import incoming_requests

from .forms import (
    LanguageForm,
    LoginForm,
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
        login(request, user)
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
    if request.method == "POST":
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
        "profile_form": profile_form, "language_form": language_form,
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
