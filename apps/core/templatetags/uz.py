from django import template

from apps.core.dates import format_date

register = template.Library()


@register.filter
def uzdate(value):
    """A date or datetime in natural Uzbek, e.g. 27-sentabr 2026-yil / 2026 йил 27 сентябрь."""
    return format_date(value)


@register.filter
def uzmonth(value):
    """Month name of a date: sentabr / сентябрь."""
    from apps.core.dates import month_name

    return month_name(value.month) if value else ""
