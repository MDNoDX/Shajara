from django.contrib import admin

from .models import Notification, NotificationSettings


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "enabled", "telegram_enabled", "days_before", "last_generated")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "occasion_date", "created_at", "read_at", "telegram_sent_at")
    list_filter = ("kind",)
