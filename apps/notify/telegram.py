"""A minimal Telegram Bot API client (standard library only).

Configuration (environment): TELEGRAM_BOT_TOKEN. The bot's @username is read
from Telegram itself (getMe), so it always matches the token;
TELEGRAM_BOT_USERNAME is only a fallback when Telegram cannot be reached.

Linking an account: the settings page shows a short one-time code. The user
either opens the bot through a button / QR code (Telegram sends
"/start <code>") or simply sends the code to the bot. The bot stores the chat
id on that user's settings.
"""
import datetime
import hashlib
import json
import logging
import re
import secrets
import urllib.error
import urllib.request

from django.conf import settings
from django.utils import timezone, translation
from django.utils.html import escape
from django.utils.translation import gettext as _

from apps.core.languages import normalize_language

from .models import BotState, NotificationSettings

log = logging.getLogger(__name__)
TOKEN_TTL = datetime.timedelta(hours=1)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: easy to type
CODE_LENGTH = 8
CODE_RE = re.compile(r"^[A-Z0-9]{%d}$" % CODE_LENGTH)
TELEGRAM_LANGS = ("uz", "ru", "en")  # bot command menus Telegram can localise


class TelegramError(Exception):
    def __init__(self, message, forbidden=False):
        super().__init__(message)
        self.forbidden = forbidden


def configured():
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))


def webhook_secret():
    """Secret Telegram sends back in every webhook call (A-Z, a-z, 0-9, _ and -)."""
    return settings.TELEGRAM_WEBHOOK_SECRET or hashlib.sha256(
        f"{settings.SECRET_KEY}:telegram-webhook".encode()).hexdigest()[:48]


def call(method, http_timeout=30, **params):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            description = json.loads(exc.read().decode(errors="replace")).get("description", "")
        except ValueError:
            description = ""
        raise TelegramError(f"{exc.code} {description}".strip(), forbidden=exc.code == 403) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TelegramError(str(exc)) from exc
    if not payload.get("ok"):
        raise TelegramError(payload.get("description", "error"))
    return payload["result"]


# ---------------------------------------------------------------------------
# The bot itself
# ---------------------------------------------------------------------------
def _token_fingerprint():
    return hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).hexdigest()[:16]


def bot_info(refresh=False):
    """{"username", "name"} of the bot the token belongs to (cached in the database)."""
    if not configured():
        return {}
    fingerprint = _token_fingerprint()
    if not refresh:
        try:
            cached = json.loads(BotState.get("me") or "{}")
        except ValueError:
            cached = {}
        if cached.get("token") == fingerprint:
            return cached
    try:
        me = call("getMe", http_timeout=10)
    except TelegramError as exc:
        log.warning("Telegram getMe failed: %s", exc)
        fallback = re.sub(r"^(https?://)?(t\.me/)?@?", "", getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip())
        return {"username": fallback, "name": fallback} if fallback else {}
    info = {"username": me.get("username", ""), "name": me.get("first_name", ""), "token": fingerprint}
    BotState.put("me", json.dumps(info))
    return info


def bot_username():
    return bot_info().get("username", "")


def webhook_url():
    from django.urls import reverse

    return settings.SITE_URL.rstrip("/") + reverse("notify:telegram_webhook")


def set_webhook(url=None):
    return call("setWebhook", url=url or webhook_url(), secret_token=webhook_secret(),
                allowed_updates=["message"], drop_pending_updates=False)


def webhook_info():
    return call("getWebhookInfo", http_timeout=10)


def ensure_webhook():
    """Self-healing: (re)register the webhook if Telegram points elsewhere.

    Returns True when a change was made. Only for public https sites.
    """
    if not configured() or not settings.SITE_URL.startswith("https://"):
        return False
    try:
        if webhook_info().get("url") == webhook_url():
            return False
        set_webhook()
        set_commands()
        return True
    except TelegramError as exc:
        log.warning("Telegram webhook check failed: %s", exc)
        return False


def set_commands():
    """The command menu next to the message box, in every language Telegram supports for us."""
    for lang in (None, *TELEGRAM_LANGS):
        with translation.override(lang or settings.LANGUAGE_CODE):
            commands = [
                {"command": "next", "description": _("Upcoming dates")},
                {"command": "help", "description": _("How to use the bot")},
                {"command": "stop", "description": _("Turn reminders off")},
            ]
        params = {"commands": commands}
        if lang:
            params["language_code"] = lang
        call("setMyCommands", **params)


def send_message(chat_id, text):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", disable_web_page_preview=True)


def send_document(chat_id, filename, data, caption=""):
    """Upload a file to a chat (multipart/form-data; Telegram accepts up to 50 MB)."""
    import uuid

    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (("chat_id", str(chat_id)), ("caption", caption)):
        if value:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\n'
                  "Content-Type: application/octet-stream\r\n\r\n").encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendDocument", data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise TelegramError(f"{exc.code}", forbidden=exc.code == 403) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TelegramError(str(exc)) from exc
    if not payload.get("ok"):
        raise TelegramError(payload.get("description", "error"))
    return payload["result"]


# ---------------------------------------------------------------------------
# Linking a site account
# ---------------------------------------------------------------------------
def _new_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _i in range(CODE_LENGTH))


def link_code(prefs, renew=False):
    """A valid one-time code for this user (reused while it has 10+ minutes left)."""
    fresh = (prefs.telegram_token and prefs.telegram_token_at
             and timezone.now() - prefs.telegram_token_at < TOKEN_TTL - datetime.timedelta(minutes=10)
             and CODE_RE.match(prefs.telegram_token))
    if renew or not fresh:
        prefs.telegram_token = _new_code()
        prefs.telegram_token_at = timezone.now()
        prefs.save(update_fields=["telegram_token", "telegram_token_at"])
    return prefs.telegram_token


def link_urls(prefs, renew=False):
    """Everything the settings page needs to connect Telegram, or {} if the bot is unknown."""
    name = bot_username()
    if not name:
        return {}
    code = link_code(prefs, renew)
    return {
        "bot": name,
        "code": code,
        # Opens the Telegram app directly (not a browser tab with Telegram Web).
        "app": f"tg://resolve?domain={name}&start={code}",
        "web": f"https://t.me/{name}?start={code}",
    }


def normalize_code(text):
    return re.sub(r"[\s\-_]", "", text or "").upper()


def _reply(chat_id, text):
    try:
        send_message(chat_id, text)
    except TelegramError as exc:
        log.warning("Telegram reply failed: %s", exc)


def _language(prefs):
    return (normalize_language(prefs.user.preferred_language) if prefs else None) or settings.LANGUAGE_CODE


def _link(chat, code):
    """Connect the chat to the account that owns `code`. Returns the settings or None."""
    code = normalize_code(code)
    if not CODE_RE.match(code):
        return None
    prefs = NotificationSettings.objects.filter(telegram_token=code).select_related("user").first()
    if not prefs or not prefs.telegram_token_at or timezone.now() - prefs.telegram_token_at >= TOKEN_TTL:
        return None
    chat_id = chat["id"]
    NotificationSettings.objects.filter(telegram_chat_id=chat_id).exclude(pk=prefs.pk).update(
        telegram_chat_id=None, telegram_enabled=False)
    prefs.telegram_chat_id = chat_id
    prefs.telegram_enabled = True
    prefs.telegram_name = (chat.get("username") or chat.get("first_name") or "")[:100]
    prefs.telegram_token = ""
    prefs.save()
    return prefs


def _help_text(linked):
    lines = [_("Hello! This bot sends reminders from your family tree: birthdays, anniversaries, memorial days and family events.")]
    if linked:
        lines += ["", _("/next — upcoming dates"), _("/stop — turn reminders off")]
    else:
        lines += ["", _("To connect, open Settings → Reminders on the site and send me the code shown there.")]
    return "\n".join(escape(line) for line in lines)


def handle_update(update):
    from . import service

    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat = message.get("chat") or {}
    if not chat.get("id") or chat.get("type") != "private" or not text:
        return
    command, _sep, arg = text.partition(" ")
    command = command.split("@")[0].lower() if command.startswith("/") else ""

    # "/start CODE" from a button or QR code, or the code typed by hand.
    code = arg.strip() if command == "/start" else ("" if command else text)
    if code:
        prefs = _link(chat, code)
        if prefs:
            with translation.override(_language(prefs)):
                _reply(chat["id"], escape(_("Your account is connected. Reminders about birthdays and family events will come here. Send /stop to turn them off.")))
                _reply(chat["id"], service.upcoming_text(prefs.user))
            service.send_pending(prefs, ignore_hour=True)
            return
        if command == "/start" or CODE_RE.match(normalize_code(code)):
            with translation.override(settings.LANGUAGE_CODE):
                _reply(chat["id"], escape(_("This code is not valid or has expired. Open Settings → Reminders on the site: a new code is shown there.")))
            return

    prefs = NotificationSettings.objects.filter(telegram_chat_id=chat["id"]).select_related("user").first()
    with translation.override(_language(prefs)):
        if command == "/stop" and prefs:
            prefs.telegram_enabled = False
            prefs.save(update_fields=["telegram_enabled"])
            _reply(chat["id"], escape(_("Reminders are turned off. Send /start to turn them on again.")))
        elif command == "/start" and prefs:
            if not prefs.telegram_enabled:
                prefs.telegram_enabled = True
                prefs.save(update_fields=["telegram_enabled"])
            _reply(chat["id"], escape(_("Reminders are on.")) + "\n\n" + service.upcoming_text(prefs.user))
        elif command == "/next" and prefs:
            _reply(chat["id"], service.upcoming_text(prefs.user))
        else:
            _reply(chat["id"], _help_text(bool(prefs)))


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


def qr_svg(data):
    """Inline SVG QR code (scan with a phone camera to open the bot)."""
    import segno

    return segno.make(data, error="m").svg_inline(scale=5, border=2, dark="#1f1a3d", light="#ffffff")
