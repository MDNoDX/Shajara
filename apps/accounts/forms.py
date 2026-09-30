from django import forms
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import password_validation
from django.utils import translation
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.core import timezones
from apps.core.languages import LATIN, language_choices, normalize_language
from apps.core.text import normalize_apostrophes
from apps.genealogy.models import Person

from .models import Gender, Palette, User

USERNAME_HELP = _("Letters, digits and the characters @ . + - _ only.")


def _password_help():
    return password_validation.password_validators_help_text_html()


class RegisterForm(auth_forms.UserCreationForm):
    first_name = forms.CharField(label=_("First name"), max_length=100)
    last_name = forms.CharField(label=_("Last name"), max_length=100)
    email = forms.EmailField(label=_("Email"))
    gender = forms.ChoiceField(label=_("Gender"), choices=Gender.choices, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "gender")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Username")
        self.fields["username"].help_text = USERNAME_HELP
        self.fields["password1"].label = _("Password")
        self.fields["password1"].help_text = _password_help()
        self.fields["password2"].label = _("Confirm password")
        self.fields["password2"].help_text = _("Enter the same password again.")
        self.fields["username"].widget.attrs["autocomplete"] = "username"

    def clean_first_name(self):
        return normalize_apostrophes(self.cleaned_data["first_name"].strip())

    def clean_last_name(self):
        return normalize_apostrophes(self.cleaned_data["last_name"].strip())

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email address already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.preferred_language = normalize_language(get_language()) or LATIN
        if commit:
            user.save()
            person = Person.objects.create(
                owner=user, first_name=user.first_name, last_name=user.last_name, gender=user.gender,
            )
            user.person = person
            user.save(update_fields=["person"])
        return user


class LoginForm(auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Username")
        self.fields["password"].label = _("Password")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "gender")
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email"),
            "gender": _("Gender"),
        }
        widgets = {"gender": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = Gender.choices
        self.fields["email"].required = True

    def clean_first_name(self):
        return normalize_apostrophes(self.cleaned_data["first_name"].strip())

    def clean_last_name(self):
        return normalize_apostrophes(self.cleaned_data["last_name"].strip())


class PreferencesForm(forms.ModelForm):
    """Language, colours and time zone: how the site looks and when reminders come."""

    class Meta:
        model = User
        fields = ["preferred_language", "palette", "time_zone"]
        labels = {"preferred_language": _("Language"), "palette": _("Colours"), "time_zone": _("Time zone")}
        widgets = {"preferred_language": forms.RadioSelect, "palette": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_language"].choices = language_choices()
        self.fields["palette"].choices = Palette.choices
        self.fields["time_zone"] = forms.ChoiceField(
            label=_("Time zone"), choices=timezones.choices(),
            help_text=_("Reminders are made for your date and sent at your hour."),
        )


class ImportArchiveForm(forms.Form):
    file = forms.FileField(label=_("Archive file (JSON)"))

    def clean_file(self):
        import json

        upload = self.cleaned_data["file"]
        if upload.size > 20 * 1024 * 1024:
            raise forms.ValidationError(_("The file is too large."))
        try:
            data = json.loads(upload.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise forms.ValidationError(_("This is not a Shajara archive file.")) from None
        if not isinstance(data, dict) or data.get("format") != "shajara-archive-1":
            raise forms.ValidationError(_("This is not a Shajara archive file."))
        return data


class PasswordChangeForm(auth_forms.PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = _("Current password")
        self.fields["new_password1"].label = _("New password")
        self.fields["new_password1"].help_text = _password_help()
        self.fields["new_password2"].label = _("Confirm the new password")
        self.fields["new_password2"].help_text = _("Enter the same password again.")


class PasswordResetForm(auth_forms.PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = _("Email")

    def send_mail(self, subject_template_name, email_template_name, context, *args, **kwargs):
        # The email is written in the recipient's own interface language.
        lang = normalize_language(getattr(context.get("user"), "preferred_language", None)) or get_language()
        with translation.override(lang):
            super().send_mail(subject_template_name, email_template_name, context, *args, **kwargs)


class SetPasswordForm(auth_forms.SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = _("New password")
        self.fields["new_password1"].help_text = _password_help()
        self.fields["new_password2"].label = _("Confirm the new password")
        self.fields["new_password2"].help_text = _("Enter the same password again.")


class CompleteProfileForm(forms.Form):
    """For accounts created through Google: the details the family tree needs."""

    first_name = forms.CharField(label=_("First name"), max_length=100)
    last_name = forms.CharField(label=_("Last name"), max_length=100, required=False)
    gender = forms.ChoiceField(label=_("Gender"), choices=Gender.choices, widget=forms.RadioSelect)

    def clean_first_name(self):
        return normalize_apostrophes(self.cleaned_data["first_name"].strip())

    def clean_last_name(self):
        return normalize_apostrophes(self.cleaned_data["last_name"].strip())

    def save(self, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.gender = self.cleaned_data["gender"]
        user.person = Person.objects.create(
            owner=user, first_name=user.first_name, last_name=user.last_name, gender=user.gender,
        )
        user.save()
        return user
