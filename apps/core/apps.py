from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"

    def ready(self):
        # Django ships no LANG_INFO entry for Uzbek Cyrillic; register one so
        # get_language_info() works for every code in settings.LANGUAGES.
        from django.conf.locale import LANG_INFO

        LANG_INFO.setdefault(
            "uz-cyrl",
            {"bidi": False, "code": "uz-cyrl", "name": "Uzbek (Cyrillic)", "name_local": "Ўзбекча"},
        )
