from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationSettings(models.Model):
    """What a user wants to be reminded of, and how."""

    DAYS_BEFORE = [(0, _("On the day")), (1, _("One day before")), (3, _("Three days before")),
                   (7, _("One week before"))]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notify")
    enabled = models.BooleanField(_("reminders are on"), default=True)
    days_before = models.PositiveSmallIntegerField(_("remind in advance"), choices=DAYS_BEFORE, default=1)
    birthdays = models.BooleanField(_("birthdays of relatives"), default=True)
    friends = models.BooleanField(_("birthdays of friends"), default=True)
    anniversaries = models.BooleanField(_("wedding anniversaries"), default=True)
    memorials = models.BooleanField(_("memorial days"), default=True)
    events = models.BooleanField(_("family events"), default=True)
    muchal = models.BooleanField(_("muchal years"), default=True)

    telegram_enabled = models.BooleanField(_("send to Telegram"), default=False)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    telegram_name = models.CharField(max_length=100, blank=True)
    telegram_token = models.CharField(max_length=40, blank=True, db_index=True)
    telegram_token_at = models.DateTimeField(null=True, blank=True)
    send_hour = models.PositiveSmallIntegerField(_("send at (hour)"), default=8)
    # Administrators: a weekly copy of the whole database to their Telegram.
    backup_telegram = models.BooleanField(default=False)

    last_generated = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("notification settings")
        verbose_name_plural = _("notification settings")

    @classmethod
    def for_user(cls, user):
        obj, _created = cls.objects.get_or_create(user=user)
        return obj


class Notification(models.Model):
    """One reminder. Text is rendered when shown, in the reader's language."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    key = models.CharField(max_length=160)
    kind = models.CharField(max_length=30)
    params = models.JSONField(default=dict)
    url = models.CharField(max_length=300, blank=True)
    occasion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    telegram_sent_at = models.DateTimeField(null=True, blank=True)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="unique_notification_key")]

    @property
    def text(self):
        from .messages import render

        return render(self)


class BotState(models.Model):
    """Small key/value store for the Telegram worker (update offset)."""

    key = models.CharField(max_length=50, primary_key=True)
    value = models.TextField(blank=True)

    @classmethod
    def get(cls, key, default=""):
        obj = cls.objects.filter(key=key).first()
        return obj.value if obj else default

    @classmethod
    def put(cls, key, value):
        cls.objects.update_or_create(key=key, defaults={"value": str(value)})


class PushSubscription(models.Model):
    """A browser or phone that asked for reminders as push notifications."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    device = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
