"""Django's own user-facing messages, re-translated by this project.

Django ships an Uzbek (Latin) catalogue, but its apostrophes are inconsistent
(o', o‘, oʻ mixed) and there is no Uzbek Cyrillic catalogue at all. Catalogues
in LOCALE_PATHS take precedence over Django's, so every Django message a user
can see is translated again in locale/*/django.po.

This module only exists so that `makemessages` keeps those msgids in the
catalogues; nothing imports it at runtime. The msgids must match Django's
source text exactly (including the curly apostrophes in “didn’t”).
"""
from django.utils.translation import gettext_noop as _
from django.utils.translation import ngettext_lazy

FORM_FIELDS = [
    _("This field is required."),
    _("Enter a whole number."),
    _("Enter a number."),
    _("Enter a valid date."),
    _("Enter a valid value."),
    _("Enter a valid email address."),
    _("Enter a valid URL."),
    _("Select a valid choice. %(value)s is not one of the available choices."),
    _("Select a valid choice. That choice is not one of the available choices."),
    _("Ensure this value is less than or equal to %(limit_value)s."),
    _("Ensure this value is greater than or equal to %(limit_value)s."),
    _("Null characters are not allowed."),
    _("No file was submitted. Check the encoding type on the form."),
    _("No file was submitted."),
    _("The submitted file is empty."),
    _("Upload a valid image. The file you uploaded was either not an image or a corrupted image."),
    _("Please either submit a file or check the clear checkbox, not both."),
    # ClearableFileInput (photo field).
    _("Currently"),
    _("Change"),
    _("Clear"),
]

LENGTH = [
    ngettext_lazy(
        "Ensure this value has at most %(limit_value)d character (it has %(show_value)d).",
        "Ensure this value has at most %(limit_value)d characters (it has %(show_value)d).",
        "limit_value",
    ),
    ngettext_lazy(
        "Ensure this value has at least %(limit_value)d character (it has %(show_value)d).",
        "Ensure this value has at least %(limit_value)d characters (it has %(show_value)d).",
        "limit_value",
    ),
    ngettext_lazy(
        "Ensure this filename has at most %(max)d character (it has %(length)d).",
        "Ensure this filename has at most %(max)d characters (it has %(length)d).",
        "max",
    ),
]

AUTH = [
    _("The two password fields didn’t match."),
    _("Enter the same password as before, for verification."),
    _("Please enter a correct %(username)s and password. Note that both fields may be case-sensitive."),
    _("This account is inactive."),
    _("Your old password was entered incorrectly. Please enter it again."),
    _("A user with that username already exists."),
    _("Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters."),
    _("This password is too common."),
    _("This password is entirely numeric."),
    _("The password is too similar to the %(verbose_name)s."),
    _("Your password can’t be too similar to your other personal information."),
    _("Your password can’t be a commonly used password."),
    _("Your password can’t be entirely numeric."),
    # Field names that Django inserts into the messages above.
    _("username"),
    _("first name"),
    _("last name"),
    _("email address"),
    ngettext_lazy(
        "This password is too short. It must contain at least %d character.",
        "This password is too short. It must contain at least %d characters.",
        "min_length",
    ),
    ngettext_lazy(
        "Your password must contain at least %(min_length)d character.",
        "Your password must contain at least %(min_length)d characters.",
        "min_length",
    ),
]
