from django import forms

from .models import NotificationSettings


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = NotificationSettings
        fields = ["enabled", "days_before", "birthdays", "friends", "anniversaries", "memorials", "events",
                  "muchal", "send_hour"]
        widgets = {"days_before": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["days_before"].choices = NotificationSettings.DAYS_BEFORE
        self.fields["send_hour"] = forms.TypedChoiceField(
            label=self.fields["send_hour"].label, coerce=int,
            choices=[(h, f"{h:02d}:00") for h in range(6, 23)], initial=self.instance.send_hour,
        )
