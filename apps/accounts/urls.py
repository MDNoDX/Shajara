from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("kirish/", views.LoginView.as_view(), name="login"),
    path("chiqish/", auth_views.LogoutView.as_view(), name="logout"),
    path("royxatdan-otish/", views.register, name="register"),
    path("profil/", views.profile, name="profile"),
    path("sozlamalar/", views.settings_view, name="settings"),
    path("sozlamalar/parol/", views.password_change, name="password_change"),
    path("parol/tiklash/", views.password_reset, name="password_reset"),
    path("parol/tiklash/yuborildi/", views.password_reset_done, name="password_reset_done"),
    path("parol/tiklash/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("parol/tiklash/tayyor/", views.password_reset_complete, name="password_reset_complete"),
]
