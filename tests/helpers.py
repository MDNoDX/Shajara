import re
from html.parser import HTMLParser

import polib
from django.conf import settings

from apps.accounts.models import User
from apps.genealogy.models import Marriage, Person

PASSWORD = "sinov-parol-2026"


class VisibleText(HTMLParser):
    """Text a user can see or hear: text nodes plus a few attributes."""

    SKIP = {"script", "style"}
    ATTRS = ("placeholder", "title", "aria-label", "alt")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        for name, value in attrs:
            if name in self.ATTRS and value:
                self.parts.append(value)

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def visible_text(html):
    parser = VisibleText()
    parser.feed(html)
    return "\n".join(parser.parts)


def english_msgids():
    """English source strings that must never reach an Uzbek page."""
    po = polib.pofile(str(settings.BASE_DIR / "locale" / "uz" / "LC_MESSAGES" / "django.po"))
    ids = set()
    for e in po:
        for text in filter(None, (e.msgid, e.msgid_plural)):
            plain = re.sub(r"%\(\w+\)[sd]|\{\w+\}|%[sd]", "", text).strip()
            if len(plain) >= 5 and re.search(r"[a-z]{3}", plain):
                ids.add(plain)
    return ids


def make_family(cyrillic=False, username="timur"):
    """A small family around `timur`, with names in the requested script."""
    n = (lambda lat, cyr: cyr if cyrillic else lat)
    user = User.objects.create_user(
        username, f"{username}@example.com", PASSWORD,
        first_name=n("Timur", "Тимур"), last_name=n("Nurmatov", "Нурматов"), gender="male",
        preferred_language="uz-cyrl" if cyrillic else "uz",
    )

    def person(first, last, gender, year=None, **kw):
        return Person.objects.create(owner=user, first_name=first, last_name=last, gender=gender, birth_year=year, **kw)

    p = {}
    p["grandpa"] = person(n("Karim", "Карим"), n("Nurmatov", "Нурматов"), "male", 1928, death_year=2001)
    p["grandma"] = person(n("Malika", "Малика"), n("Nurmatova", "Нурматова"), "female", 1931)
    p["father"] = person(n("Rustam", "Рустам"), n("Nurmatov", "Нурматов"), "male", 1956, father=p["grandpa"], mother=p["grandma"])
    p["mother"] = person(n("Gulnora", "Гулнора"), n("Nurmatova", "Нурматова"), "female", 1959)
    p["aunt"] = person(n("Dilnoza", "Дилноза"), n("Aliyeva", "Алиева"), "female", 1960, father=p["grandpa"], mother=p["grandma"])
    p["uncle_in_law"] = person(n("Sherzod", "Шерзод"), n("Aliyev", "Алиев"), "male", 1957)
    p["cousin"] = person(n("Kamila", "Камила"), n("Aliyeva", "Алиева"), "female", 1985, father=p["uncle_in_law"], mother=p["aunt"])
    p["me"] = person(n("Timur", "Тимур"), n("Nurmatov", "Нурматов"), "male", 1984, father=p["father"], mother=p["mother"],
                     birth_month=9, birth_day=27, biography=n("Dasturchi.", "Дастурчи."))
    p["older_brother"] = person(n("Jasur", "Жасур"), n("Nurmatov", "Нурматов"), "male", 1980, father=p["father"], mother=p["mother"])
    p["younger_sister"] = person(n("Laylo", "Лайло"), n("Nurmatova", "Нурматова"), "female", 1990, father=p["father"], mother=p["mother"])
    p["wife"] = person(n("Aziza", "Азиза"), n("Nurmatova", "Нурматова"), "female", 1987)
    p["son"] = person(n("Samir", "Самир"), n("Nurmatov", "Нурматов"), "male", 2012, father=p["me"], mother=p["wife"])
    p["grandson"] = person(n("Anvar", "Анвар"), n("Nurmatov", "Нурматов"), "male", None, father=p["son"])
    p["brothers_wife"] = person(n("Nigora", "Нигора"), n("Karimova", "Каримова"), "female", 1982)
    for husband, wife in [("grandpa", "grandma"), ("father", "mother"), ("uncle_in_law", "aunt"),
                          ("me", "wife"), ("older_brother", "brothers_wife")]:
        Marriage.objects.create(owner=user, husband=p[husband], wife=p[wife])
    user.person = p["me"]
    user.save()
    return user, p
