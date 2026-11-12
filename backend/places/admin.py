from django.contrib import admin

from .models import SavedPlace, TripPlace


class TripPlaceInline(admin.TabularInline):
    model = TripPlace
    extra = 0
    fields = ("trip", "added_at")
    readonly_fields = ("added_at",)


@admin.register(SavedPlace)
class SavedPlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "city", "country", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "city", "country", "address", "owner__username")
    inlines = [TripPlaceInline]


@admin.register(TripPlace)
class TripPlaceAdmin(admin.ModelAdmin):
    list_display = ("place", "trip", "added_at")
    list_filter = ("trip",)
