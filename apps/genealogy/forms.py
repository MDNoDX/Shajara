import datetime

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from apps.accounts.models import Gender
from apps.core.dates import is_valid_partial_date, month_choices, partial_date_key
from apps.core.text import normalize_apostrophes

from .models import Marriage, Person, Story
from .terminology import ADD_RELATION

SHORT_TEXT_FIELDS = ("first_name", "last_name", "patronymic", "birth_place", "death_place", "occupation", "education")


class MonthSelect(forms.Select):
    """Month names are resolved at render time, in the active language."""

    def get_context(self, name, value, attrs):
        self.choices = [("", pgettext_lazy("date part", "Month"))] + month_choices()
        return super().get_context(name, value, attrs)


def _date_fields(prefix):
    this_year = datetime.date.today().year
    return {
        f"{prefix}_day": forms.IntegerField(
            label=pgettext_lazy("date part", "Day"), required=False, min_value=1, max_value=31,
            widget=forms.NumberInput(attrs={"placeholder": pgettext_lazy("date part", "Day"), "inputmode": "numeric"}),
        ),
        f"{prefix}_month": forms.TypedChoiceField(
            label=pgettext_lazy("date part", "Month"), required=False, coerce=int, empty_value=None,
            choices=[("", "")] + [(i, str(i)) for i in range(1, 13)], widget=MonthSelect,
        ),
        f"{prefix}_year": forms.IntegerField(
            label=pgettext_lazy("date part", "Year"), required=False, min_value=1000, max_value=this_year,
            widget=forms.NumberInput(attrs={"placeholder": pgettext_lazy("date part", "Year"), "inputmode": "numeric"}),
        ),
    }


def clean_partial_date(form, prefix):
    data = form.cleaned_data
    year, month, day = data.get(f"{prefix}_year"), data.get(f"{prefix}_month"), data.get(f"{prefix}_day")
    if day and not month:
        form.add_error(f"{prefix}_month", _("If you enter the day, choose the month as well."))
    elif (day or month) and not year:
        form.add_error(f"{prefix}_year", _("Enter the year of this date as well."))
    elif not is_valid_partial_date(year, month, day):
        form.add_error(f"{prefix}_day", _("There is no such day in the chosen month."))
    elif year and partial_date_key(year, month, day) > partial_date_key(*_today_parts(month, day)):
        form.add_error(f"{prefix}_year", _("The date cannot be in the future."))
    return partial_date_key(year, month, day)


def _today_parts(month, day):
    today = datetime.date.today()
    # Compare only as precisely as the entered date.
    return today.year, today.month if month else None, today.day if day else None


def _person_label(person):
    return f"{person.full_name} ({person.lifespan})" if person.lifespan else person.full_name


class PersonForm(forms.ModelForm):
    """Personal details. Parents are chosen from the owner's archive."""

    def __init__(self, *args, owner, archive=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.archive = archive
        self.fields.update(_date_fields("birth"))
        self.fields.update(_date_fields("death"))
        for prefix in ("birth", "death"):
            for part in ("year", "month", "day"):
                self.fields[f"{prefix}_{part}"].initial = getattr(self.instance, f"{prefix}_{part}")
        self.fields["gender"].widget = forms.RadioSelect(choices=Gender.choices)
        self.fields["gender"].choices = Gender.choices

        people = Person.objects.filter(owner=owner)
        if self.instance.pk:
            excluded = {self.instance.pk}
            if archive:
                excluded |= archive.descendants(self.instance.pk)
            people = people.exclude(pk__in=excluded)
        if "father" in self.fields:
            self.fields["father"].queryset = people.filter(gender=Gender.MALE)
            self.fields["mother"].queryset = people.filter(gender=Gender.FEMALE)
            for name in ("father", "mother"):
                self.fields[name].empty_label = pgettext_lazy("choice", "— not specified —")
                self.fields[name].label_from_instance = _person_label
            self.fields["father"].label = pgettext_lazy("person form", "Father")
            self.fields["mother"].label = pgettext_lazy("person form", "Mother")

    class Meta:
        model = Person
        fields = [
            "first_name", "last_name", "patronymic", "gender",
            "birth_place", "is_deceased", "death_place",
            "occupation", "education", "biography", "life_story", "photo",
            "father", "mother",
        ]
        widgets = {
            "biography": forms.Textarea(attrs={"rows": 4}),
            "life_story": forms.Textarea(attrs={"rows": 8}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean(self):
        data = super().clean()
        for name in SHORT_TEXT_FIELDS:
            if data.get(name):
                data[name] = normalize_apostrophes(data[name].strip())
        birth = clean_partial_date(self, "birth")
        death = clean_partial_date(self, "death")
        if birth and death and death < birth and not self.has_error("death_year"):
            self.add_error("death_year", _("The date of death cannot be earlier than the date of birth."))
        if data.get("death_year"):
            data["is_deceased"] = True
        self._check_parents(data)
        return data

    def _check_parents(self, data):
        pk = self.instance.pk
        for name in ("father", "mother"):
            parent = data.get(name)
            if not parent or not pk:
                continue
            if parent.pk == pk:
                self.add_error(name, _("A person cannot be their own parent."))
            elif self.archive and pk in self.archive.ancestors(parent.pk):
                self.add_error(name, _("This link would make a person their own ancestor."))

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and hasattr(photo, "size") and photo.size > settings.PHOTO_MAX_BYTES:
            raise forms.ValidationError(
                _("The photo is too large. The maximum size is %(size)d MB."),
                params={"size": settings.PHOTO_MAX_BYTES // (1024 * 1024)},
            )
        return photo

    def save(self, commit=True):
        person = super().save(commit=False)
        person.owner = self.owner
        for prefix in ("birth", "death"):
            for part in ("year", "month", "day"):
                setattr(person, f"{prefix}_{part}", self.cleaned_data.get(f"{prefix}_{part}"))
        if commit:
            person.save()
        return person


class RelativeForm(PersonForm):
    """A new person linked to an existing one as father, mother, spouse, child or sibling.

    Instead of creating a new person, an existing one can be linked.
    """

    relation = forms.ChoiceField(label=_("Relationship"), choices=list(ADD_RELATION.items()))
    existing = forms.ModelChoiceField(
        label=_("Or link someone already in the tree"), queryset=Person.objects.none(), required=False,
    )

    class Meta(PersonForm.Meta):
        fields = [f for f in PersonForm.Meta.fields if f not in ("father", "mother")]

    def __init__(self, *args, anchor, **kwargs):
        super().__init__(*args, **kwargs)
        self.anchor = anchor
        for name in ("father", "mother"):
            self.fields.pop(name, None)
        self.fields["first_name"].required = False
        self.fields["gender"].required = False
        excluded = {anchor.pk}
        self.fields["existing"].queryset = Person.objects.filter(owner=self.owner).exclude(pk__in=excluded)
        self.fields["existing"].empty_label = pgettext_lazy("choice", "— add a new person —")
        self.fields["existing"].label_from_instance = _person_label
        self.order_fields(["relation", "existing"])

    def _check_parents(self, data):
        pass

    def clean(self):
        data = super().clean()
        relation = data.get("relation")
        existing = data.get("existing")
        anchor = self.anchor
        if not existing:
            if not data.get("first_name"):
                self.add_error("first_name", _("Choose an existing person or enter the new person's first name."))
            if not data.get("gender") and relation not in ("father", "mother"):
                self.add_error("gender", _("Choose the gender."))
        gender = existing.gender if existing else data.get("gender")
        if relation == "father":
            data["gender"] = Gender.MALE if not existing else gender
            if anchor.father_id:
                self.add_error("relation", _("This person already has a father in the tree."))
            elif existing and existing.gender != Gender.MALE:
                self.add_error("existing", _("The father must be a man."))
        elif relation == "mother":
            data["gender"] = Gender.FEMALE if not existing else gender
            if anchor.mother_id:
                self.add_error("relation", _("This person already has a mother in the tree."))
            elif existing and existing.gender != Gender.FEMALE:
                self.add_error("existing", _("The mother must be a woman."))
        elif relation == "spouse":
            if gender and gender == anchor.gender:
                self.add_error("existing" if existing else "gender", _("A husband and wife must be a man and a woman."))
            elif existing:
                husband, wife = (anchor, existing) if anchor.is_male else (existing, anchor)
                if Marriage.objects.filter(husband=husband, wife=wife).exists():
                    self.add_error("existing", _("These two people are already recorded as married."))
        elif relation == "sibling":
            if not anchor.father_id and not anchor.mother_id:
                self.add_error("relation", _("To add a brother or sister, first add this person's father or mother."))
        elif relation == "child" and existing:
            taken = existing.father_id if anchor.is_male else existing.mother_id
            if taken and taken != anchor.pk:
                if anchor.is_male:
                    self.add_error("existing", _("This person already has a father in the tree."))
                else:
                    self.add_error("existing", _("This person already has a mother in the tree."))
        if existing and self.archive and relation in ("father", "mother", "child"):
            parent, child = (anchor, existing) if relation == "child" else (existing, anchor)
            if parent.pk in self.archive.descendants(child.pk) or parent.pk == child.pk:
                self.add_error("existing", _("This link would make a person their own ancestor."))
        return data

    def _post_clean(self):
        # Linking an existing person: the new-person fields stay empty.
        if self.cleaned_data.get("existing"):
            return
        super()._post_clean()

    def save(self, commit=True):
        relation = self.cleaned_data["relation"]
        anchor = self.anchor
        person = self.cleaned_data.get("existing") or super().save(commit=True)
        if relation == "father":
            anchor.father = person
            anchor.save()
        elif relation == "mother":
            anchor.mother = person
            anchor.save()
        elif relation == "child":
            if anchor.is_male:
                person.father = anchor
                spouse_field = "mother"
            else:
                person.mother = anchor
                spouse_field = "father"
            other = self.cleaned_data.get("other_parent")
            if other and getattr(person, f"{spouse_field}_id") is None:
                setattr(person, spouse_field, other)
            person.save()
        elif relation == "sibling":
            person.father = person.father or anchor.father
            person.mother = person.mother or anchor.mother
            person.save()
        elif relation == "spouse":
            husband, wife = (anchor, person) if anchor.is_male else (person, anchor)
            Marriage.objects.get_or_create(owner=self.owner, husband=husband, wife=wife)
        return person


class RelativeWithSpouseForm(RelativeForm):
    """Adds the choice of the child's other parent when the anchor has spouses."""

    other_parent = forms.ModelChoiceField(
        label=_("The child's other parent"), queryset=Person.objects.none(), required=False,
    )

    def __init__(self, *args, spouses=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["other_parent"].queryset = Person.objects.filter(pk__in=[s.pk for s in spouses])
        self.fields["other_parent"].empty_label = pgettext_lazy("choice", "— not specified —")
        if len(spouses) == 1:
            self.fields["other_parent"].initial = spouses[0].pk


class MarriageForm(forms.ModelForm):
    class Meta:
        model = Marriage
        fields = ["year", "is_divorced"]
        widgets = {"year": forms.NumberInput(attrs={"inputmode": "numeric"})}


class StoryForm(forms.ModelForm):
    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.filter(owner=owner)
        self.fields["person"].empty_label = pgettext_lazy("choice", "— the whole family —")
        self.fields["person"].required = False
        self.fields["year"].widget.attrs["inputmode"] = "numeric"

    class Meta:
        model = Story
        fields = ["title", "person", "year", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 12})}

    def clean_title(self):
        return normalize_apostrophes(self.cleaned_data["title"].strip())
