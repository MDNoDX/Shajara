"""Creating reminders for a day and delivering them to Telegram."""
import datetime
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone, translation
from django.utils.html import escape
from django.utils.translation import gettext as _

from apps.core.dates import format_date
from apps.core.languages import normalize_language
from apps.core.timezones import zone

from . import telegram
from .messages import render_parts, telegram_text
from .models import Notification, NotificationSettings
from .occasions import occasions

log = logging.getLogger(__name__)


def user_today(user):
    """Today in the user's own time zone."""
    return timezone.localdate(timezone=zone(getattr(user, "time_zone", None)))


def generate(user, today=None):
    """Create today's reminders for `user` (safe to call many times a day)."""
    today = today or user_today(user)
    prefs = NotificationSettings.for_user(user)
    created = 0
    if prefs.enabled:
        lead = prefs.days_before
        for o in occasions(user, today, today + datetime.timedelta(days=lead), prefs):
            days_left = (o.date - today).days
            if days_left not in (0, lead):
                continue
            _obj, new = Notification.objects.get_or_create(
                user=user, key=f"{o.key}:{days_left}",
                defaults={"kind": o.kind, "params": {**o.params, "days_left": days_left},
                          "url": o.url, "occasion_date": o.date},
            )
            created += new
    if prefs.last_generated != today:
        prefs.last_generated = today
        prefs.save(update_fields=["last_generated"])
    return created


def ensure_today(user):
    """Called on page views: generate once per day without a background worker."""
    prefs = NotificationSettings.for_user(user)
    if prefs.last_generated != user_today(user):
        generate(user)


def send_pending(prefs, now=None, ignore_hour=False):
    """Send one user's unsent reminders of today and yesterday to Telegram."""
    if not (telegram.configured() and prefs.enabled and prefs.telegram_enabled and prefs.telegram_chat_id):
        return 0
    now = timezone.localtime(now or timezone.now(), zone(prefs.user.time_zone))
    if not ignore_hour and now.hour < prefs.send_hour:
        return 0
    pending = Notification.objects.filter(user=prefs.user, telegram_sent_at=None,
                                          created_at__date__gte=now.date() - datetime.timedelta(days=1))
    lang = normalize_language(prefs.user.preferred_language) or settings.LANGUAGE_CODE
    sent = 0
    for n in pending.order_by("occasion_date", "id"):
        with translation.override(lang):
            text = telegram_text(n)
        try:
            telegram.send_message(prefs.telegram_chat_id, text)
        except telegram.TelegramError as exc:
            log.warning("Telegram send failed for user %s: %s", prefs.user_id, exc)
            if exc.forbidden:  # the user blocked the bot
                prefs.telegram_enabled = False
                prefs.save(update_fields=["telegram_enabled"])
            break
        n.telegram_sent_at = timezone.now()
        n.save(update_fields=["telegram_sent_at"])
        sent += 1
    return sent


def send_pending_telegram(now=None, ignore_hour=False):
    """Send due reminders to everyone who linked Telegram (called every hour)."""
    if not telegram.configured():
        return 0
    return sum(send_pending(prefs, now, ignore_hour) for prefs in NotificationSettings.objects.filter(
        enabled=True, telegram_enabled=True).exclude(telegram_chat_id=None).select_related("user"))


def upcoming_text(user, days=30, limit=12):
    """Telegram message with the next dates (for /next and after connecting)."""
    today = user_today(user)
    items = occasions(user, today, today + datetime.timedelta(days=days))[:limit]
    if not items:
        return escape(_("No dates in the next %(days)d days.") % {"days": days})
    lines = [f"<b>{escape(_('Upcoming dates'))}</b>"]
    for o in items:
        parts = render_parts(o.kind, o.params, (o.date - today).days)
        lines.append(f"{parts['icon']} {escape(format_date(o.date))} — {escape(parts['title'])}")
    return "\n".join(lines)


def test_message(prefs):
    with translation.override(normalize_language(prefs.user.preferred_language) or settings.LANGUAGE_CODE):
        text = "✅ " + escape(_("Test message: Telegram reminders work.")) + "\n\n" + upcoming_text(prefs.user)
    telegram.send_message(prefs.telegram_chat_id, text)


def run_daily(today=None):
    total = 0
    for user in get_user_model().objects.filter(is_active=True):
        total += generate(user, today)
    return total
