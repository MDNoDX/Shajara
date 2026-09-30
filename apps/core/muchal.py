"""Muchal — the twelve-year animal cycle as counted in Uzbekistan.

The Uzbek muchal year begins at Navroʻz (21 March), not at the Chinese new
year: someone born on 10 February 2006 belongs to the previous year's animal.
When only the birth year is known the animal of that year is given and marked
as uncertain (it is wrong only for births from 1 January to 20 March).
"""
import datetime

from django.utils.translation import pgettext_lazy

# Index 0 is Sichqon (rat); 2020 was a Sichqon year.
ANIMALS = [
    ("sichqon", pgettext_lazy("muchal", "Rat")),
    ("sigir", pgettext_lazy("muchal", "Ox")),
    ("yolbars", pgettext_lazy("muchal", "Tiger")),
    ("quyon", pgettext_lazy("muchal", "Rabbit")),
    ("baliq", pgettext_lazy("muchal", "Dragon")),
    ("ilon", pgettext_lazy("muchal", "Snake")),
    ("ot", pgettext_lazy("muchal", "Horse")),
    ("qoy", pgettext_lazy("muchal", "Sheep")),
    ("maymun", pgettext_lazy("muchal", "Monkey")),
    ("tovuq", pgettext_lazy("muchal", "Rooster")),
    ("it", pgettext_lazy("muchal", "Dog")),
    ("tongiz", pgettext_lazy("muchal", "Pig")),
]
EMOJI = ["🐭", "🐮", "🐯", "🐰", "🐟", "🐍", "🐴", "🐑", "🐵", "🐓", "🐶", "🐷"]
NAVROZ = (3, 21)


def muchal_year(year, month=None, day=None):
    """The muchal cycle year a date belongs to (it starts at Navroʻz)."""
    if month and (month, day or 1) < NAVROZ:
        return year - 1
    return year


def animal_index(year):
    return (year - 2020) % 12


def muchal(year, month=None, day=None):
    """{"code", "name", "emoji", "year", "certain"} or None without a year."""
    if not year:
        return None
    cycle = muchal_year(year, month, day)
    i = animal_index(cycle)
    certain = bool(month and day) or (month is not None and month > 3)
    return {"code": ANIMALS[i][0], "name": str(ANIMALS[i][1]), "emoji": EMOJI[i], "year": cycle, "certain": certain}


def current_cycle_year(today=None):
    today = today or datetime.date.today()
    return muchal_year(today.year, today.month, today.day)


def next_muchal_year(year, month=None, day=None, today=None):
    """The next cycle year (from this one on) with the person's animal."""
    info = muchal(year, month, day)
    if not info:
        return None
    now = current_cycle_year(today)
    n = info["year"]
    while n < now:
        n += 12
    return n
