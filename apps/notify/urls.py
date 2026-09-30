from django.urls import path

from . import views

app_name = "notify"

urlpatterns = [
    path("xabarlar/", views.notification_list, name="list"),
    path("xabarlar/<int:pk>/", views.notification_open, name="open"),
    path("xabarlar/oqildi/", views.mark_all_read, name="read_all"),
    path("xabarlar/holat.json", views.status, name="status"),
    path("sozlamalar/eslatmalar/", views.notification_settings, name="settings"),
    path("sozlamalar/eslatmalar/telegram/", views.telegram_connect, name="telegram_connect"),
    path("sozlamalar/eslatmalar/telegram/uzish/", views.telegram_disconnect, name="telegram_disconnect"),
    path("sozlamalar/eslatmalar/telegram/holat.json", views.telegram_status, name="telegram_status"),
    path("sozlamalar/eslatmalar/telegram/sinov/", views.telegram_test, name="telegram_test"),
    path("sozlamalar/eslatmalar/telegram/pauza/", views.telegram_toggle, name="telegram_toggle"),
    path("sozlamalar/eslatmalar/push/yoqish/", views.push_subscribe, name="push_subscribe"),
    path("sozlamalar/eslatmalar/push/ochirish/", views.push_unsubscribe, name="push_unsubscribe"),
    path("sozlamalar/eslatmalar/push/sinov/", views.push_test, name="push_test"),
    path("cron/kunlik/", views.cron_daily, name="cron_daily"),
    path("telegram/webhook/", views.telegram_webhook, name="telegram_webhook"),
]
