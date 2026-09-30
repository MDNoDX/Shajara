"""A minimal Telegram Bot API client (standard library only).

Configuration (environment): TELEGRAM_BOT_TOKEN and, optionally,
TELEGRAM_BOT_USERNAME. Linking works through a one-time token:
the settings page opens t.me/<bot>?start=<token>, the bot receives
"/start <token>" and stores the chat id on that user's settings.
"""
import datetime
import json
import logging
import secrets
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language

from .models import BotState, NotificationSettings

log = logging.getLogger(__name__)
TOKEN_TTL = datetime.timedelta(hours=1)


class TelegramError(Exception):
    def __init__(self, message, forbidden=False):
        super().__init__(message)
        self.forbidden = forbidden


def configured():
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))


def call(method, http_timeout=30, **params):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise TelegramError(f"{exc.code} {body}", forbidden=exc.code == 403) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TelegramError(str(exc)) from exc
    if not payload.get("ok"):
        raise TelegramError(payload.get("description", "error"))
    return payload["result"]


def bot_username():
    name = getattr(settings, "TELEGRAM_BOT_USERNAME", "")
    if name or not configured():
        return name.lstrip("@")
    cached = BotState.get("username")
    if not cached:
        try:
            cached = call("getMe", http_timeout=10)["username"]
            BotState.put("username", cached)
        except TelegramError:
            return ""
    return cached


def send_message(chat_id, text):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)


def new_link_token(prefs):
    prefs.telegram_token = secrets.token_urlsafe(18)
    prefs.telegram_token_at = timezone.now()
    prefs.save(update_fields=["telegram_token", "telegram_token_at"])
    return prefs.telegram_token


def link_url(prefs):
    name = bot_username()
    if not name:
        return ""
    return f"https://t.me/{name}?start={new_link_token(prefs)}"


def _reply(chat_id, text):
    try:
        send_message(chat_id, text)
    except TelegramError as exc:
        log.warning("Telegram reply failed: %s", exc)


def handle_update(update):
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id or chat.get("type") != "private":
        return
    command, _sep, arg = text.partition(" ")
    command = command.split("@")[0]
    if command == "/start" and arg:
        prefs = NotificationSettings.objects.filter(telegram_token=arg.strip()).select_related("user").first()
        valid = prefs and prefs.telegram_token_at and timezone.now() - prefs.telegram_token_at < TOKEN_TTL
        if not valid:
            with translation.override("uz"):
                _reply(chat_id, _("This link has expired. Open the settings page on the site and press “Connect Telegram” again."))
            return
        NotificationSettings.objects.filter(telegram_chat_id=chat_id).exclude(pk=prefs.pk).update(
            telegram_chat_id=None, telegram_enabled=False)
        prefs.telegram_chat_id = chat_id
        prefs.telegram_enabled = True
        prefs.telegram_name = (chat.get("username") or chat.get("first_name") or "")[:100]
        prefs.telegram_token = ""
        prefs.save()
        with translation.override(normalize_language(prefs.user.preferred_language) or "uz"):
            _reply(chat_id, _("Your account is connected. Reminders about birthdays and family events will come here. Send /stop to turn them off."))
        return
    prefs = NotificationSettings.objects.filter(telegram_chat_id=chat_id).select_related("user").first()
    lang = normalize_language(prefs.user.preferred_language) if prefs else "uz"
    with translation.override(lang or "uz"):
        if command == "/stop" and prefs:
            prefs.telegram_enabled = False
            prefs.save(update_fields=["telegram_enabled"])
            _reply(chat_id, _("Reminders are turned off. You can turn them on again in the site settings."))
        else:
            _reply(chat_id, _("Hello! This bot sends reminders from your family tree. To connect it, open Settings on the site and press “Connect Telegram”."))


def poll_once(timeout=25):
    offset = int(BotState.get("offset", "0") or 0)
    updates = call("getUpdates", http_timeout=timeout + 10, offset=offset, timeout=timeout,
                   allowed_updates=["message"])
    for update in updates:
        try:
            handle_update(update)
        finally:
            BotState.put("offset", update["update_id"] + 1)
    return len(updates)
