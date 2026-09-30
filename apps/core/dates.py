"""Dates in natural language.

Genealogy dates are often partial (only a year, or a month and a year), so
people store year / month / day separately. Output:
    Uzbek Latin     27-sentabr 2026-yil · 2026-yil sentabr · 2026-yil
    Uzbek Cyrillic  2026 йил 27 сентябрь · 2026 йил сентябрь · 2026 йил
    Russian         27 сентября 2026 г. · сентябрь 2026 г. · 2026 г.
    English         September 27, 2026 · September 2026 · 2026
"""
import calendar
import datetime

from django.utils import timezone
from django.utils.translation import gettext, pgettext, pgettext_lazy

MONTHS = [
    pgettext_lazy("month name", "January"),
    pgettext_lazy("month name", "February"),
    pgettext_lazy("month name", "March"),
    pgettext_lazy("month name", "April"),
    pgettext_lazy("month name", "May"),
    pgettext_lazy("month name", "June"),
    pgettext_lazy("month name", "July"),
    pgettext_lazy("month name", "August"),
    pgettext_lazy("month name", "September"),
    pgettext_lazy("month name", "October"),
    pgettext_lazy("month name", "November"),
    pgettext_lazy("month name", "December"),
]


# The month inside a full date ("27 сентября"): Russian uses the genitive
# case here; Uzbek and English use the same word as above.
MONTHS_IN_DATE = [
    pgettext_lazy("month name in a date", "January"),
    pgettext_lazy("month name in a date", "February"),
    pgettext_lazy("month name in a date", "March"),
    pgettext_lazy("month name in a date", "April"),
    pgettext_lazy("month name in a date", "May"),
    pgettext_lazy("month name in a date", "June"),
    pgettext_lazy("month name in a date", "July"),
    pgettext_lazy("month name in a date", "August"),
    pgettext_lazy("month name in a date", "September"),
    pgettext_lazy("month name in a date", "October"),
    pgettext_lazy("month name in a date", "November"),
    pgettext_lazy("month name in a date", "December"),
]


def month_name(month):
    return str(MONTHS[month - 1])


def month_in_date(month):
    return str(MONTHS_IN_DATE[month - 1])


def month_choices():
    """(1, "Yanvar") … for select boxes; capitalised because it starts a line."""
    return [(i, month_name(i)[:1].upper() + month_name(i)[1:]) for i in range(1, 13)]


def format_partial_date(year, month=None, day=None):
    if not year:
        return ""
    if month and day:
        return pgettext("full date", "{month} {day}, {year}").format(
            day=day, month=month_in_date(month), year=year
        )
    if month:
        return pgettext("month and year", "{month} {year}").format(month=month_name(month), year=year)
    return pgettext("year only", "{year}").format(year=year)


def format_date(value):
    """Format a date or datetime (converted to local time) in full."""
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        value = timezone.localtime(value) if timezone.is_aware(value) else value
        value = value.date()
    return format_partial_date(value.year, value.month, value.day)


def format_lifespan(birth_year, death_year, is_deceased):
    """Short years for cards and tree nodes: "1928–2001", "1956", "?–1998"."""
    if birth_year and death_year:
        return f"{birth_year}–{death_year}"
    if death_year:
        return f"?–{death_year}"
    if birth_year:
        return f"{birth_year}–?" if is_deceased else str(birth_year)
    return gettext("years unknown") if is_deceased else ""


def is_valid_partial_date(year, month, day):
    if day and not month:
        return False
    if month and not 1 <= month <= 12:
        return False
    if day:
        # Without a year, allow 29 February (a leap year is assumed).
        return 1 <= day <= calendar.monthrange(year or 2000, month)[1]
    return True


def partial_date_key(year, month=None, day=None):
    """Sortable tuple; unknown parts sort as the middle of their range."""
    if not year:
        return None
    return (year, month or 6, day or 15)


def age_between(y, m, d, end_y, end_m=None, end_d=None):
    """Whole years between two partial dates, or None if unknown.

    With unknown months the result may be one year too high; callers show it
    as approximate when `birth` or `end` lacks a month and day.
    """
    if not y or not end_y:
        return None
    years = end_y - y
    if m and end_m and (end_m, end_d or 31) < (m, d or 1):
        years -= 1
    return years if years >= 0 else None
