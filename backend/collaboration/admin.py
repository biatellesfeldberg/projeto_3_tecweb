from django.contrib import admin

from .models import Friendship, TripMembership


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "sender",
        "recipient",
        "status",
        "created_at",
    ]

    list_filter = ["status"]

    search_fields = [
        "sender__email",
        "recipient__email",
    ]

@admin.register(TripMembership)
class TripMembershipAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "trip",
        "user",
        "invited_by",
        "status",
    ]

    list_filter = ["status"]