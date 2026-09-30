from django.contrib import admin

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "person", "owner", "how_met")
    search_fields = ("name",)
