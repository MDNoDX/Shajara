from django.contrib import admin

from .models import Marriage, Person, Story


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("full_name", "owner", "gender", "birth_year", "death_year")
    search_fields = ("first_name", "last_name", "search_key")
    list_filter = ("gender",)
    raw_id_fields = ("father", "mother", "owner")


admin.site.register(Marriage)
admin.site.register(Story)
