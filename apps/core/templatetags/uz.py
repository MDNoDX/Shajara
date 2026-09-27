from django import template

from apps.core.dates import format_date

register = template.Library()


@register.filter
def uzdate(value):
    """A date or datetime in natural Uzbek, e.g. 27-sentabr 2026-yil / 2026 йил 27 сентябрь."""
    return format_date(value)
