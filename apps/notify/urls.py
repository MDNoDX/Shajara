from django.urls import path

from . import views

app_name = "notify"

urlpatterns = [
    path("xabarlar/", views.notification_list, name="list"),
    path("xabarlar/<int:pk>/", views.notification_open, name="open"),
    path("xabarlar/oqildi/", views.mark_all_read, name="read_all"),
    path("sozlamalar/eslatmalar/", views.notification_settings, name="settings"),
    path("sozlamalar/eslatmalar/telegram/", views.telegram_connect, name="telegram_connect"),
    path("sozlamalar/eslatmalar/telegram/uzish/", views.telegram_disconnect, name="telegram_disconnect"),
]
