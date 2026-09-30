from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse, reverse_lazy
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language

from .forms import (
    CompleteProfileForm,
    ImportArchiveForm,
    LoginForm,
    PasswordChangeForm,
    PreferencesForm,
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
    """The old "My profile" page: everything it showed now lives in Settings."""
    return redirect("accounts:settings")


def _save_person_name(user):
    """Keep the user's own record in the tree in step with the account."""
    if user.person:
        user.person.first_name = user.first_name
        user.person.last_name = user.last_name
        if user.gender:
            user.person.gender = user.gender
        user.person.save()


@login_required
def settings_view(request):
    """Settings → General: personal details, language, colours, time zone."""
    user = request.user
    profile_form = ProfileForm(instance=user, prefix="profile")
    prefs_form = PreferencesForm(instance=user, prefix="prefs")
    if request.method == "POST" and "save_profile" in request.POST:
        profile_form = ProfileForm(request.POST, instance=user, prefix="profile")
        if profile_form.is_valid():
            profile_form.save()
            _save_person_name(user)
            messages.success(request, _("The information has been saved."))
            return redirect("accounts:settings")
    elif request.method == "POST" and "save_prefs" in request.POST:
        old_language = user.preferred_language
        prefs_form = PreferencesForm(request.POST, instance=user, prefix="prefs")
        if prefs_form.is_valid():
            prefs_form.save()
            translation.activate(user.preferred_language)
            if user.preferred_language != old_language:
                messages.success(request, _("The interface language has been changed."))
            else:
                messages.success(request, _("The information has been saved."))
            from apps.notify.models import NotificationSettings

            NotificationSettings.objects.filter(user=user).update(last_generated=None)
            return redirect(reverse("accounts:settings") + "#appearance")
    return render(request, "accounts/settings.html", {
        "profile_form": profile_form, "prefs_form": prefs_form, "settings_tab": "general",
    })


@login_required
def security_view(request):
    """Settings → Security: password, Google, other devices."""
    user = request.user
    has_password = user.has_usable_password()
    form_class = PasswordChangeForm if has_password else SetPasswordForm
    form = form_class(user, request.POST or None) if "save_password" in request.POST else form_class(user)
    if request.method == "POST" and "save_password" in request.POST and form.is_valid():
        form.save()
        update_session_auth_hash(request, user)
        messages.success(request, _("Your password has been changed.") if has_password
                         else _("The password has been set. You can now sign in with it too."))
        return redirect(reverse("accounts:security") + "#password")
    google = user.socialaccount_set.filter(provider="google").first()
    return render(request, "accounts/settings_security.html", {
        "form": form, "has_password": has_password, "google_account": google,
        "google_email": (google.extra_data or {}).get("email", "") if google else "",
        "other_sessions": _other_sessions(request).count(), "settings_tab": "security",
    })


def _other_sessions(request):
    from django.contrib.sessions.models import Session

    keys = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()).exclude(
            session_key=request.session.session_key).iterator():
        if str(session.get_decoded().get("_auth_user_id")) == str(request.user.pk):
            keys.append(session.session_key)
    return Session.objects.filter(session_key__in=keys)


@require_POST
@login_required
def sign_out_others(request):
    count, _details = _other_sessions(request).delete()
    messages.success(request, _("You have been signed out on your other devices."))
    return redirect(reverse("accounts:security") + "#devices")


@require_POST
@login_required
def google_disconnect(request):
    user = request.user
    if not user.has_usable_password():
        messages.error(request, _("Set a password first, otherwise you could not sign in any more."))
    else:
        user.socialaccount_set.filter(provider="google").delete()
        messages.info(request, _("Google has been disconnected from your account."))
    return redirect(reverse("accounts:security") + "#google")


@login_required
def data_view(request):
    """Settings → Your data: downloads, import, deleting the account."""
    from django.db import transaction

    from apps.genealogy.archive_io import import_archive
    from apps.genealogy.models import Person

    user = request.user
    people = Person.objects.filter(owner=user)
    can_import = people.count() <= 1
    form = ImportArchiveForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not can_import:
            messages.error(request, _("An archive can only be imported into an empty family tree."))
            return redirect("accounts:data")
        if form.is_valid():
            with transaction.atomic():
                own = user.person
                user.person = None
                user.save(update_fields=["person"])
                if own:
                    own.delete()
                counts = import_archive(user, form.cleaned_data["file"])
            messages.success(request, _("The archive has been imported: %(people)d people.") % counts)
            return redirect("genealogy:tree")
    return render(request, "accounts/settings_data.html", {
        "form": form, "can_import": can_import, "people_count": people.count(),
        "friends_count": user.contacts.count(), "stories_count": user.stories.count(),
        "events_count": user.events.count(),
        "settings_tab": "data",
    })


@login_required
def password_change(request):
    """Old address: the password form now lives in Settings → Security."""
    return redirect(reverse("accounts:security") + "#password")


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
