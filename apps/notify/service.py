"""Creating reminders for a day and delivering them to Telegram."""
import datetime
import logging

from django.contrib.auth import get_user_model
from django.utils import timezone, translation

from apps.core.languages import normalize_language

from . import telegram
from .messages import telegram_text
from .models import Notification, NotificationSettings
from .occasions import occasions

log = logging.getLogger(__name__)


def generate(user, today=None):
    """Create today's reminders for `user` (safe to call many times a day)."""
    today = today or timezone.localdate()
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
    if prefs.last_generated != timezone.localdate():
        generate(user)


def send_pending_telegram(now=None):
    """Send today's unsent reminders to users who linked Telegram."""
    if not telegram.configured():
        return 0
    now = timezone.localtime(now or timezone.now())
    sent = 0
    for prefs in NotificationSettings.objects.filter(enabled=True, telegram_enabled=True).exclude(
            telegram_chat_id=None).select_related("user"):
        if now.hour < prefs.send_hour:
            continue
        pending = Notification.objects.filter(user=prefs.user, telegram_sent_at=None,
                                              created_at__date__gte=now.date() - datetime.timedelta(days=1))
        lang = normalize_language(prefs.user.preferred_language) or "uz"
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


def run_daily(today=None):
    total = 0
    for user in get_user_model().objects.filter(is_active=True):
        total += generate(user, today)
    return total
