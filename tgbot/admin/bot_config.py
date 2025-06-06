
import telebot
from django.contrib import admin
from django.utils.html import format_html

from solo.admin import SingletonModelAdmin

from tgbot.models import TelegramBotToken, Configuration

##############################Add commentMore actions
# TelegramBotToken Admin
##############################
@admin.register(TelegramBotToken)
class TelegramBotTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'test_bot', 'token', 'bot_link')
    search_fields = ('id', 'token', 'name')
    readonly_fields = ('bot_link', )

    def bot_link(self, obj: TelegramBotToken):
        if not obj.token:
            return "Bot token is not defined"
        try:
            bot_instance = telebot.TeleBot(obj.token)
            bot_info = bot_instance.get_me()
            return format_html(
                '<a href="https://t.me/{}" target="_blank">https://t.me/{}</a>',
                bot_info.username,
                bot_info.username,
            )
        except Exception as e:
            return f"Ошибка: {e}"
    bot_link.short_description = "Ссылка на бота"

##############################
# Configuration Admin (Singleton)Add commentMore actions
##############################
@admin.register(Configuration)
class ConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        (None, {'fields': ('test_mode',)}),
    )
