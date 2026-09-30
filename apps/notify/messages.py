"""Reminder texts, rendered in the reader's language when shown or sent."""
from django.utils.html import escape
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext

from apps.core.dates import format_date
from apps.core.muchal import ANIMALS
from apps.genealogy.models import Event

from .occasions import ICONS


def when(days_left):
    if days_left == 0:
        return pgettext("reminder", "Today")
    if days_left == 1:
        return pgettext("reminder", "Tomorrow")
    return ngettext("In %(days)d day", "In %(days)d days", days_left) % {"days": days_left}


def render_parts(kind, params, days_left=0):
    """{"title", "body", "icon"} for an occasion or a stored notification."""
    w = when(days_left)
    age, years = params.get("age"), params.get("years")
    if kind == "birthday":
        title = _("Birthday: {name}").format(name=params["name"])
        body = (_("{when} they turn {age}.").format(when=w, age=age) if age
                else _("{when} is their birthday.").format(when=w))
    elif kind == "friend_birthday":
        title = _("Friend's birthday: {name}").format(name=params["name"])
        body = (_("{when} they turn {age}.").format(when=w, age=age) if age
                else _("{when} is their birthday.").format(when=w))
        body += " " + _("Friend of {whose}.").format(whose=params["whose"])
    elif kind == "memorial":
        title = _("Memorial day: {name}").format(name=params["name"])
        body = (_("{when} it will be {years} years since they passed away.").format(when=w, years=years) if years
                else _("{when} is the day they passed away.").format(when=w))
    elif kind == "anniversary":
        title = _("Wedding anniversary: {names}").format(names=params["names"])
        body = (_("{when} they will have been married for {years} years.").format(when=w, years=years) if years
                else _("{when} is their wedding anniversary.").format(when=w))
    elif kind == "event":
        kind_label = dict(Event.Kind.choices).get(params.get("kind"), "")
        title = params.get("title") or str(kind_label)
        body = _("{when}.").format(when=w)
        if years:
            body = _("{when} it will be {years} years since then.").format(when=w, years=years)
        if params.get("place"):
            body += " " + _("Place: {place}.").format(place=params["place"])
    elif kind == "muchal":
        animal = str(ANIMALS[params["animal"]][1])
        title = _("Muchal year: {animal}").format(animal=animal)
        body = _("A {animal} year begins at Navroʻz. It is the muchal year of: {names}.").format(
            animal=animal, names=", ".join(params["names"]))
    else:
        title, body = params.get("title", ""), ""
    return {"title": title, "body": body, "icon": ICONS.get(kind, "📅")}


def render(notification):
    parts = render_parts(notification.kind, notification.params, notification.params.get("days_left", 0))
    if notification.occasion_date:
        parts["date"] = format_date(notification.occasion_date)
    return parts


def telegram_text(notification):
    parts = render(notification)
    lines = [f"{parts['icon']} <b>{escape(parts['title'])}</b>", escape(parts["body"])]
    if parts.get("date"):
        lines.append(f"<i>{escape(parts['date'])}</i>")
    return "\n".join(lines)
