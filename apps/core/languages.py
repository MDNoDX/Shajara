"""Interface languages and how they are named to users.

Uzbek (Latin) is the main language; Uzbek (Cyrillic), Russian and English
are full translations of the same catalogue.
"""
from django.conf import settings

LATIN = "uz"
CYRILLIC = "uz-cyrl"
RUSSIAN = "ru"
ENGLISH = "en"

# Each language is named in its own language, as users look for it in the
# switcher; these self-names are deliberately not passed through gettext.
LANGUAGE_LABELS = {
    LATIN: "Oʻzbekcha",
    CYRILLIC: "Ўзбекча",
    RUSSIAN: "Русский",
    ENGLISH: "English",
}
# Second line in the language chooser: the script, again in that language.
LANGUAGE_NOTES = {
    LATIN: "lotin yozuvi",
    CYRILLIC: "кирилл ёзуви",
    RUSSIAN: "",
    ENGLISH: "",
}
LANGUAGE_SHORT = {LATIN: "UZ", CYRILLIC: "ЎЗ", RUSSIAN: "RU", ENGLISH: "EN"}
# Value for the HTML lang attribute (BCP 47).
HTML_LANG = {LATIN: "uz-Latn", CYRILLIC: "uz-Cyrl", RUSSIAN: "ru", ENGLISH: "en"}
# Languages written in Cyrillic (search hints, audits).
CYRILLIC_SCRIPT = {CYRILLIC, RUSSIAN}
# Guests are not switched to these by their browser language: the site
# opens in Uzbek until they choose otherwise.
EXPLICIT_ONLY = {RUSSIAN, ENGLISH}


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


def language_options(current):
    return [
        {"code": code, "label": LANGUAGE_LABELS[code], "note": LANGUAGE_NOTES[code],
         "short": LANGUAGE_SHORT[code], "html_lang": HTML_LANG[code], "active": code == current}
        for code in supported_codes()
    ]
