# tgbot/admin/subscription.py

from django.contrib import admin

from tgbot.models import DailySubscription


@admin.register(DailySubscription)
class DailySubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "send_time", "created_at")
    search_fields = ("user__username", "user__chat_id")
    list_filter = ("send_time",)
    readonly_fields = ("created_at",)
