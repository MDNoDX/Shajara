from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Family tree"), {"fields": ("preferred_language", "gender", "person")}),
    )
    list_display = ("username", "first_name", "last_name", "email", "preferred_language", "is_staff")
