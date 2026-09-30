from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Invite, Membership, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Family tree"), {"fields": ("preferred_language", "time_zone", "gender", "person", "own_person", "active_archive")}),
        # Untick to let someone in who has lost both the phone and the recovery codes.
        (_("Two-step sign-in"), {"fields": ("totp_enabled",)}),
    )
    raw_id_fields = ("person", "own_person", "active_archive")
    list_display = ("username", "first_name", "last_name", "email", "preferred_language", "totp_enabled", "is_staff")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("owner", "member", "role", "created_at")
    list_filter = ("role",)
    raw_id_fields = ("owner", "member", "person")


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("owner", "role", "created_at", "accepted_by", "accepted_at")
    raw_id_fields = ("owner", "created_by", "person", "accepted_by")
    exclude = ("token",)
