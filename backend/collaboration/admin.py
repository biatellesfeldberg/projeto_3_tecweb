from django.contrib import admin

from .models import Friendship


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