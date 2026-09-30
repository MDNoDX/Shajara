from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotifyConfig(AppConfig):
    name = "apps.notify"
    label = "notify"
    verbose_name = _("Notifications")
