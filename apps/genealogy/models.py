import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Gender
from apps.core.dates import format_lifespan, format_partial_date, partial_date_key
from apps.core.text import search_key


def photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    return f"photos/{instance.owner_id}/{uuid.uuid4().hex}.{ext}"


class Person(models.Model):
    """One person in a user's family archive.

    Names, places and texts are user content: they are stored exactly as
    entered (apart from normalising Uzbek apostrophes in short fields) and are
    never transliterated. `search_key` is a derived, script-independent copy
    used only for searching.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="people", verbose_name=_("owner")
    )
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100, blank=True)
    patronymic = models.CharField(_("patronymic"), max_length=100, blank=True)
    gender = models.CharField(_("gender"), max_length=10, choices=Gender.choices)

    birth_year = models.PositiveSmallIntegerField(_("year of birth"), null=True, blank=True)
    birth_month = models.PositiveSmallIntegerField(_("month of birth"), null=True, blank=True)
    birth_day = models.PositiveSmallIntegerField(_("day of birth"), null=True, blank=True)
    birth_place = models.CharField(_("place of birth"), max_length=200, blank=True)

    is_deceased = models.BooleanField(_("deceased"), default=False)
    death_year = models.PositiveSmallIntegerField(_("year of death"), null=True, blank=True)
    death_month = models.PositiveSmallIntegerField(_("month of death"), null=True, blank=True)
    death_day = models.PositiveSmallIntegerField(_("day of death"), null=True, blank=True)
    death_place = models.CharField(_("place of death"), max_length=200, blank=True)

    occupation = models.CharField(_("occupation"), max_length=200, blank=True)
    education = models.CharField(_("education"), max_length=200, blank=True)
    biography = models.TextField(_("biography"), blank=True)
    life_story = models.TextField(_("life story"), blank=True)
    photo = models.ImageField(_("photo"), upload_to=photo_path, blank=True)

    father = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children_as_father",
        verbose_name=_("father"),
    )
    mother = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children_as_mother",
        verbose_name=_("mother"),
    )

    search_key = models.TextField(editable=False, blank=True, default="", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("person")
        verbose_name_plural = _("people")
        ordering = ["last_name", "first_name", "id"]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if self.death_year:
            self.is_deceased = True
        self.search_key = search_key(self.first_name, self.last_name, self.patronymic)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("genealogy:person", args=[self.pk])

    @property
    def full_name(self):
        return " ".join(p for p in (self.last_name, self.first_name, self.patronymic) if p)

    @property
    def short_name(self):
        return " ".join(p for p in (self.first_name, self.last_name) if p)

    @property
    def is_male(self):
        return self.gender == Gender.MALE

    @property
    def birth_date_display(self):
        return format_partial_date(self.birth_year, self.birth_month, self.birth_day)

    @property
    def death_date_display(self):
        return format_partial_date(self.death_year, self.death_month, self.death_day)

    @property
    def lifespan(self):
        return format_lifespan(self.birth_year, self.death_year, self.is_deceased)

    @property
    def birth_key(self):
        return partial_date_key(self.birth_year, self.birth_month, self.birth_day)

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()


class Marriage(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="marriages")
    husband = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="marriages_as_husband",
                                verbose_name=_("husband"))
    wife = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="marriages_as_wife",
                             verbose_name=_("wife"))
    year = models.PositiveSmallIntegerField(_("year of marriage"), null=True, blank=True)
    is_divorced = models.BooleanField(_("divorced"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("marriage")
        verbose_name_plural = _("marriages")
        constraints = [models.UniqueConstraint(fields=["husband", "wife"], name="unique_marriage")]
        ordering = ["year", "id"]

    def partner_of(self, person):
        return self.wife if person.pk == self.husband_id else self.husband


class Story(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    person = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="stories",
                               verbose_name=_("about whom"))
    title = models.CharField(_("title"), max_length=200)
    body = models.TextField(_("text"))
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("story")
        verbose_name_plural = _("stories")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("genealogy:story", args=[self.pk])
