from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GenealogyConfig(AppConfig):
    name = "apps.genealogy"
    label = "genealogy"
    verbose_name = _("Family tree")
