from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from apps.core.languages import LATIN, language_choices
from apps.core.text import search_key


class Gender(models.TextChoices):
    MALE = "male", pgettext_lazy("gender", "Male")
    FEMALE = "female", pgettext_lazy("gender", "Female")


class Palette(models.TextChoices):
    ATLAS = "atlas", pgettext_lazy("palette", "Atlas")
    OSMON = "osmon", pgettext_lazy("palette", "Sky")
    BOG = "bog", pgettext_lazy("palette", "Garden")
    ANOR = "anor", pgettext_lazy("palette", "Pomegranate")


class User(AbstractUser):
    preferred_language = models.CharField(
        _("interface language"), max_length=10, choices=language_choices(), default=LATIN
    )
    gender = models.CharField(_("gender"), max_length=10, choices=Gender.choices, blank=True)
    palette = models.CharField(_("colours"), max_length=10, choices=Palette.choices, default=Palette.ATLAS)
    # The person in the user's own family tree who represents them.
    person = models.OneToOneField(
        "genealogy.Person",
        verbose_name=_("own record in the family tree"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="account",
    )
    search_key = models.TextField(editable=False, blank=True, default="")

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def save(self, *args, **kwargs):
        self.search_key = search_key(self.first_name, self.last_name, self.username)
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username
