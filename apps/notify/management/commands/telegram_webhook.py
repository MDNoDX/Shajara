"""Register the Telegram webhook for serverless hosting (Vercel).

    python manage.py telegram_webhook            # uses SITE_URL
    python manage.py telegram_webhook --url https://example.uz
    python manage.py telegram_webhook --info
    python manage.py telegram_webhook --delete   # back to polling (run_worker)
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from apps.notify import telegram


class Command(BaseCommand):
    help = "Set, show or delete the Telegram webhook."

    def add_arguments(self, parser):
        parser.add_argument("--url", help="Public address of the site (default: SITE_URL)")
        parser.add_argument("--info", action="store_true")
        parser.add_argument("--delete", action="store_true")

    def handle(self, *args, **opts):
        if not telegram.configured():
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")
        if opts["info"]:
            self.stdout.write(str(telegram.call("getWebhookInfo")))
            return
        if opts["delete"]:
            telegram.call("deleteWebhook")
            self.stdout.write("Webhook deleted.")
            return
        base = (opts["url"] or settings.SITE_URL).rstrip("/")
        if not base.startswith("https://"):
            raise CommandError("Telegram needs an https:// address.")
        url = base + reverse("notify:telegram_webhook")
        telegram.set_webhook(url)
        self.stdout.write(self.style.SUCCESS(f"Webhook set: {url}"))
