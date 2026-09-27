from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FriendsConfig(AppConfig):
    name = "apps.friends"
    label = "friends"
    verbose_name = _("Friends")
