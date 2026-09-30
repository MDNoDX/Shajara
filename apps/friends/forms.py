from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.text import normalize_apostrophes
from apps.genealogy.forms import DatePartsMixin, _person_label
from apps.genealogy.models import Person

from .models import Contact


class ContactForm(DatePartsMixin, forms.ModelForm):
    date_prefix, date_target, date_require_year = "birth", "birth_", False

    def __init__(self, *args, owner, default_person=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner_user = owner
        self.fields["person"].queryset = Person.objects.filter(owner=owner).order_by("first_name", "last_name")
        self.fields["person"].label_from_instance = _person_label
        self.fields["person"].empty_label = None
        if default_person and not self.instance.pk and not self.initial.get("person"):
            self.initial["person"] = default_person
        self.fields["how_met"].choices = [("", "—")] + list(Contact.HowMet.choices)
        self.fields["phone"].widget.attrs.update({"inputmode": "tel", "autocomplete": "off"})
        self.add_date_fields()
        self.order_fields(["person", "name", "how_met", "birth_day", "birth_month", "birth_year", "phone", "note"])

    class Meta:
        model = Contact
        fields = ["person", "name", "how_met", "phone", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"note": _("For example: where they met, what they did together.")}

    def clean(self):
        data = super().clean()
        self.clean_date_parts()
        if data.get("name"):
            data["name"] = normalize_apostrophes(data["name"].strip())
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.owner = self.owner_user
        self.store_date_parts(obj)
        if commit:
            obj.save()
        return obj
