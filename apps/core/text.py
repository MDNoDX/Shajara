"""Uzbek text helpers: apostrophes and script-independent search keys.

Apostrophes
    The interface uses one representation everywhere:
      Oʻ oʻ Gʻ gʻ  — U+02BB MODIFIER LETTER TURNED COMMA
      ʼ            — U+02BC MODIFIER LETTER APOSTROPHE (tutuq belgisi: maʼlumot)
    Both are Unicode *letters*, so words such as "oʻgʻil" are not split by
    word-boundary rules, double-click selection or search tokenisation.

Search keys
    People may be entered in Latin or Cyrillic. The stored value is never
    changed; instead a separate, folded key is derived for searching, so
    "Alisher", "Алишер" and "alisher" all produce the same key.
"""
import re
import unicodedata

OKINA = "ʻ"  # ʻ
TUTUQ = "ʼ"  # ʼ

# Every character people type for the Uzbek apostrophes.
APOSTROPHE_VARIANTS = "'‘’`´ʻʼ′ʹ"
_APOS = re.escape(APOSTROPHE_VARIANTS)
_OG_APOS = re.compile(rf"([oOgG])[{_APOS}]")
_TUTUQ = re.compile(rf"(?<=[^\W\d_])[{re.escape(APOSTROPHE_VARIANTS.replace(OKINA, ''))}](?=[^\W\d_])")


def normalize_apostrophes(value):
    """Bring Uzbek apostrophes to the canonical form (Oʻ, Gʻ, ʼ).

    Only the apostrophe characters change; letters are never touched.
    Used for short fields such as names and places.
    """
    if not value:
        return value
    value = _OG_APOS.sub(lambda m: m.group(1) + OKINA, value)
    return _TUTUQ.sub(TUTUQ, value)


# Uzbek Cyrillic → Latin, lower case, for search keys only.
_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d", "е": "e",
    "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "қ": "q",
    "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ў": "o", "ф": "f", "х": "x", "ҳ": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ь": "", "ы": "i", "э": "e",
    "ю": "yu", "я": "ya", "і": "i",
}
_NON_WORD = re.compile(r"[^0-9a-z\s]+")
_SPACES = re.compile(r"\s+")


def search_key(*values):
    """Fold names written in either script to one comparable key.

    Folding is deliberately forgiving (x/h, q/k, "dj"/"j", "ye"/"e")
    because older documents often use Russian spellings of Uzbek names,
    e.g. "Джамшид Кадыров" should still find "Jamshid Qodirov".
    """
    text = " ".join(v for v in values if v)
    text = unicodedata.normalize("NFKC", text).lower()
    text = "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)
    text = re.sub(f"[{_APOS}]", "", text)
    # Strip remaining accents (e.g. "é") but keep the base letter.
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text = _NON_WORD.sub(" ", text)
    text = text.replace("dj", "j").replace("x", "h").replace("q", "k")
    # Cyrillic "е" is written "ye" at the start of a word and after a vowel
    # (Елена → Yelena, Хўжаев → Xoʻjayev); fold both spellings to "e".
    text = text.replace("ye", "e")
    return _SPACES.sub(" ", text).strip()


def search_tokens(query):
    return [t for t in search_key(query).split(" ") if t]


_NAME_ENDINGS = ("jon", "boy", "bek", "xon", "жон", "бой", "бек", "хон")
_CYRILLIC = re.compile(r"[\u0400-\u04FF]")


def surname_from_name(name):
    """Uzbek surname from a (grand)father's first name, for suggestions only.

    Madaminjon → Madaminov, Nabijon → Nabiyev, Tavakiljon → Tavakilov,
    Карим → Каримов, Набижон → Набиев. The endings -jon, -boy, -bek, -xon are
    dropped, as is usual; the result keeps the script of the name and the
    user can always correct it.
    """
    word = normalize_apostrophes((name or "").strip().split(" ")[0])
    if not word:
        return ""
    base = word
    for ending in _NAME_ENDINGS:
        if base.lower().endswith(ending) and len(base) > len(ending) + 2:
            base = base[: -len(ending)]
            break
    if _CYRILLIC.search(base):
        return base + ("ев" if base[-1].lower() in "аеиоуўэюя" else "ов")
    return base + ("yev" if base[-1].lower() in "aeiou" else "ov")
