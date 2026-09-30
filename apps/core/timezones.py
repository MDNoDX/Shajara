"""Time zones people can choose: where Uzbek families usually live.

Reminders are created for the user's own date and sent to Telegram at the
hour they chose, in this zone.
"""
import zoneinfo

from django.utils.translation import pgettext_lazy

DEFAULT = "Asia/Tashkent"

ZONES = [
    ("Asia/Tashkent", pgettext_lazy("time zone", "Tashkent")),
    ("Asia/Almaty", pgettext_lazy("time zone", "Almaty")),
    ("Asia/Bishkek", pgettext_lazy("time zone", "Bishkek")),
    ("Asia/Dushanbe", pgettext_lazy("time zone", "Dushanbe")),
    ("Asia/Ashgabat", pgettext_lazy("time zone", "Ashgabat")),
    ("Europe/Moscow", pgettext_lazy("time zone", "Moscow")),
    ("Europe/Istanbul", pgettext_lazy("time zone", "Istanbul")),
    ("Asia/Dubai", pgettext_lazy("time zone", "Dubai")),
    ("Asia/Riyadh", pgettext_lazy("time zone", "Riyadh")),
    ("Asia/Seoul", pgettext_lazy("time zone", "Seoul")),
    ("Asia/Tokyo", pgettext_lazy("time zone", "Tokyo")),
    ("Asia/Shanghai", pgettext_lazy("time zone", "Beijing")),
    ("Europe/Berlin", pgettext_lazy("time zone", "Berlin")),
    ("Europe/London", pgettext_lazy("time zone", "London")),
    ("America/New_York", pgettext_lazy("time zone", "New York")),
    ("America/Chicago", pgettext_lazy("time zone", "Chicago")),
    ("America/Los_Angeles", pgettext_lazy("time zone", "Los Angeles")),
    ("Australia/Sydney", pgettext_lazy("time zone", "Sydney")),
]


def zone(name):
    try:
        return zoneinfo.ZoneInfo(name or DEFAULT)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo(DEFAULT)


def choices(now=None):
    """[(name, "Toshkent (UTC+5)"), …] with the current offset of each zone."""
    import datetime

    now = now or datetime.datetime.now(datetime.timezone.utc)
    out = []
    for name, label in ZONES:
        minutes = int(now.astimezone(zone(name)).utcoffset().total_seconds() // 60)
        sign = "+" if minutes >= 0 else "−"
        hours, rest = divmod(abs(minutes), 60)
        offset = f"UTC{sign}{hours}" + (f":{rest:02d}" if rest else "")
        out.append((name, f"{label} ({offset})"))
    return out
