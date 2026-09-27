"""The two interface languages and how they are named to users."""
from django.conf import settings

LATIN = "uz"
CYRILLIC = "uz-cyrl"

# Each language is named in its own script, as users look for it in the
# switcher; these self-names are deliberately not passed through gettext.
LANGUAGE_LABELS = {
    LATIN: "Oʻzbekcha",  # Oʻzbekcha
    CYRILLIC: "Кириллча",
}
# Value for the HTML lang attribute (BCP 47).
HTML_LANG = {LATIN: "uz-Latn", CYRILLIC: "uz-Cyrl"}


def supported_codes():
    return [code for code, _name in settings.LANGUAGES]


def normalize_language(code):
    """Return the supported language code for `code`, or None."""
    if not code:
        return None
    code = code.strip().lower()
    return code if code in supported_codes() else None


def language_choices():
    return [(code, LANGUAGE_LABELS[code]) for code in supported_codes()]
