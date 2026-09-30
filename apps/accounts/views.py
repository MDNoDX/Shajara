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

from apps.genealogy.models import Person

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
        return redirect(_after_sign_in(request))
    return render(request, "accounts/register.html", {"form": form, "next": request.GET.get("next", "")})


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
    template_name = "accounts/login.html"
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

    from . import totp
    from .forms import CodeForm

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
    return render(request, "accounts/two_factor.html", {"form": form})


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
        "recovery_left": len(user.recovery_codes or []),
    })


@login_required
def two_factor_setup(request):
    """Turn two-step sign-in on: scan the QR code, confirm with a code."""
    from apps.notify.telegram import qr_svg

    from . import totp
    from .forms import CodeForm

    user = request.user
    if user.totp_enabled:
        return redirect(reverse("accounts:security") + "#two-step")
    secret = request.session.get("totp_new") or totp.new_secret()
    request.session["totp_new"] = secret
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if totp.verify(secret, form.cleaned_data["code"]):
            codes, hashes = totp.new_recovery_codes()
            user.totp_secret, user.totp_enabled, user.recovery_codes = secret, True, hashes
            user.save(update_fields=["totp_secret", "totp_enabled", "recovery_codes"])
            request.session.pop("totp_new", None)
            return render(request, "accounts/two_factor_codes.html", {"codes": codes, "settings_tab": "security"})
        form.add_error("code", _("The code is not correct."))
    return render(request, "accounts/two_factor_setup.html", {
        "form": form, "secret": " ".join(secret[i:i + 4] for i in range(0, len(secret), 4)),
        "qr": qr_svg(totp.uri(secret, user.email or user.username)), "settings_tab": "security",
    })


@require_POST
@login_required
def two_factor_off(request):
    from . import totp

    user = request.user
    code = request.POST.get("code", "")
    if user.totp_enabled and (totp.verify(user.totp_secret, code) or totp.use_recovery_code(user, code)):
        user.totp_secret, user.totp_enabled, user.recovery_codes = "", False, []
        user.save(update_fields=["totp_secret", "totp_enabled", "recovery_codes"])
        messages.info(request, _("Two-step sign-in has been turned off."))
    else:
        messages.error(request, _("The code is not correct."))
    return redirect(reverse("accounts:security") + "#two-step")


@require_POST
@login_required
def two_factor_codes(request):
    """New recovery codes (the old ones stop working)."""
    from . import totp

    user = request.user
    if not user.totp_enabled or not totp.verify(user.totp_secret, request.POST.get("code", "")):
        messages.error(request, _("The code is not correct."))
        return redirect(reverse("accounts:security") + "#two-step")
    codes, hashes = totp.new_recovery_codes()
    user.recovery_codes = hashes
    user.save(update_fields=["recovery_codes"])
    return render(request, "accounts/two_factor_codes.html", {"codes": codes, "settings_tab": "security"})


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
    can_import = people.count() <= 1 and not user.active_archive_id
    form = ImportArchiveForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if not can_import:
            messages.error(request, _("An archive can only be imported into an empty family tree."))
            return redirect("accounts:data")
        if form.is_valid():
            with transaction.atomic():
                own = user.person
                user.person = None
                user.own_person = None
                user.save(update_fields=["person", "own_person"])
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


# ---------------------------------------------------------------------------
# Family members: invites, access, switching between family trees
# ---------------------------------------------------------------------------
@login_required
def family_view(request):
    """Settings → Family: who may see or edit my archive, and the trees I take part in."""
    from .forms import InviteForm
    from .models import Invite
    from .sharing import archives_of, open_invites

    user = request.user
    form = InviteForm(request.POST or None, owner=user)
    new_invite = None
    if request.method == "POST" and form.is_valid():
        invite = form.save(commit=False)
        invite.owner = invite.created_by = user
        invite.save()
        return redirect(f"{reverse('accounts:family')}?yangi={invite.pk}#invites")
    if request.GET.get("yangi", "").isdigit():
        new_invite = Invite.objects.filter(owner=user, pk=int(request.GET["yangi"])).first()
    return render(request, "accounts/settings_family.html", {
        "form": form, "new_invite": new_invite if new_invite and new_invite.is_open else None,
        "new_link": request.build_absolute_uri(reverse("accounts:invite", args=[new_invite.token])) if new_invite else "",
        "invites": open_invites(user),
        "members": user.members.select_related("member", "person"),
        "archives": archives_of(user),
        "own_people": Person.objects.filter(owner=user).count(),
        "settings_tab": "family",
    })


@require_POST
@login_required
def invite_revoke(request, pk):
    from .models import Invite

    Invite.objects.filter(owner=request.user, pk=pk, accepted_at=None).delete()
    messages.info(request, _("The invitation link no longer works."))
    return redirect(reverse("accounts:family") + "#invites")


@require_POST
@login_required
def member_update(request, pk):
    """Change a member's access, or remove them."""
    from .models import Membership, Role
    from .sharing import remove_member

    membership = Membership.objects.filter(owner=request.user, pk=pk).select_related("member").first()
    if membership is None:
        return redirect("accounts:family")
    if "remove" in request.POST:
        remove_member(request.user, membership.member)
        messages.info(request, _("Access has been removed."))
    elif request.POST.get("role") in Role.values:
        membership.role = request.POST["role"]
        membership.save(update_fields=["role"])
        messages.success(request, _("The information has been saved."))
    return redirect(reverse("accounts:family") + "#members")


@require_POST
@login_required
def archive_switch(request, user_id):
    """Work in another family tree (or back in my own)."""
    from django.contrib.auth import get_user_model

    from .sharing import switch_archive

    owner = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if owner is None or not switch_archive(request.user, owner):
        messages.error(request, _("Access denied."))
        return redirect("accounts:family")
    return redirect("home")


@require_POST
@login_required
def archive_leave(request, user_id):
    from django.contrib.auth import get_user_model

    from .sharing import leave

    owner = get_user_model().objects.filter(pk=user_id).first()
    if owner is not None:
        leave(request.user, owner)
        messages.info(request, _("You have left this family tree."))
    return redirect("accounts:family")


def invite_view(request, token):
    """The page an invitation link opens: sign in or up, then join."""
    from .models import Invite
    from .sharing import accept_invite, role_in

    invite = Invite.objects.filter(token=token).select_related("owner", "person").first()
    if invite is None or not invite.is_open:
        if invite and request.user.is_authenticated and role_in(request.user, invite.owner):
            return redirect("home")  # already joined with this link
        return render(request, "accounts/invite.html", {"invite": None}, status=410)
    if not request.user.is_authenticated:
        request.session["invite"] = token
        return render(request, "accounts/invite.html", {"invite": invite, "next": request.path})
    if invite.owner_id == request.user.pk:
        messages.info(request, _("This is your own invitation link: send it to a relative."))
        return redirect("accounts:family")
    if request.method == "POST":
        membership = accept_invite(invite, request.user)
        request.session.pop("invite", None)
        if membership is None:
            return render(request, "accounts/invite.html", {"invite": None}, status=410)
        messages.success(request, _("You have joined the family tree."))
        return redirect("home" if request.user.person_id else "accounts:who_am_i")
    return render(request, "accounts/invite.html", {
        "invite": invite, "own_people": Person.objects.filter(owner=request.user).count(),
    })


@login_required
def who_am_i(request):
    """After joining a shared tree: find your own record in it (optional)."""
    from .models import Membership

    owner = request.archive
    if request.method == "POST":
        person = Person.objects.filter(owner=owner, pk=request.POST.get("person") or 0).first()
        if person is not None and not hasattr(person, "account"):
            request.user.person = person
            request.user.save(update_fields=["person"])
            Membership.objects.filter(owner=owner, member=request.user).update(person=person)
        return redirect("home")
    return render(request, "accounts/who_am_i.html", {"owner": owner})


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
        return redirect(_after_sign_in(request))
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
