from django.contrib import admin


from .models import Activity, ItineraryProposal, Trip, TripDay


class TripDayInline(admin.TabularInline):
    model = TripDay
    extra = 0
    fields = ("day_number", "date", "title", "notes")


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = (
        "order",
        "start_time",
        "end_time",
        "title",
        "category",
        "location_name",
        "estimated_cost",
        "cost_type",
    )


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "destination",
        "start_date",
        "end_date",
        "travelers_count",
        "status",
    )
    list_filter = ("status", "mode", "style", "pace")
    search_fields = ("title", "origin", "destination", "owner__username")
    inlines = [TripDayInline]


@admin.register(TripDay)
class TripDayAdmin(admin.ModelAdmin):
    list_display = ("trip", "day_number", "date", "title")
    list_filter = ("trip",)
    inlines = [ActivityInline]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "day",
        "start_time",
        "category",
        "estimated_cost",
        "cost_type",
    )
    list_filter = ("category", "cost_type")
    search_fields = ("title", "location_name", "address")


@admin.register(ItineraryProposal)
class ItineraryProposalAdmin(admin.ModelAdmin):
    list_display = ("id", "trip", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("trip__title", "request")
    readonly_fields = ("created_at", "decided_at", "base_fingerprint")
