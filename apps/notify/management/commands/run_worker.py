"""Background worker: daily reminders, Telegram and push delivery, weekly backup, bot commands.

    python manage.py run_worker          # runs forever (use as a service)
    python manage.py run_worker --once   # one pass, e.g. from cron
"""
import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.notify import service, telegram

log = logging.getLogger(__name__)
REMINDER_EVERY = 10 * 60  # seconds


class Command(BaseCommand):
    help = "Create daily reminders, send them to Telegram and answer the bot."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **opts):
        last = 0.0
        while True:
            close_old_connections()
            if opts["once"] or time.monotonic() - last > REMINDER_EVERY:
                created = service.run_daily()
                sent = service.send_pending_telegram()
                pushed = service.send_pending_push()
                backups = service.weekly_backup()
                last = time.monotonic()
                self.stdout.write(f"reminders created: {created}, sent to Telegram: {sent}, "
                                  f"pushed: {pushed}, backups: {backups}")
            if opts["once"]:
                return
            if telegram.configured():
                try:
                    telegram.poll_once(timeout=25)
                except telegram.TelegramError as exc:
                    log.warning("Telegram polling failed: %s", exc)
                    time.sleep(15)
            else:
                time.sleep(60)
