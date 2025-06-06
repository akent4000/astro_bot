# tgbot/admin/apod.py

from django.contrib import admin
from solo.admin import SingletonModelAdmin

from tgbot.models import ApodApiKey, ApodFile


@admin.register(ApodApiKey)
class ApodApiKeyAdmin(SingletonModelAdmin):
    fieldsets = (
        (None, {'fields': ('api_key',)}),
    )


@admin.register(ApodFile)
class ApodFileAdmin(admin.ModelAdmin):
    list_display = ('date', 'title', 'telegram_media_id', 'created_at')
    search_fields = ('date', 'title')
    readonly_fields = ('created_at',)
    list_filter = ('date',)
