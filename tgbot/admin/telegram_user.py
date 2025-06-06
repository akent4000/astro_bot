# tgbot/admin/telegram_user.py

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect, render
from telebot import TeleBot

import telebot
from django.urls import reverse

from tgbot.models import TelegramUser, SentMessage
from tgbot.forms import SendMessageForm
from tgbot.logics.constants import Messages
from tgbot.logics.administrator_actions import mass_mailing

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        'chat_id',
        'first_name',
        'last_name',
        'username',
        'blocked',
        'bot_was_blocked',
        'is_admin',
        'send_admin_notifications',
        'admin_signature',
        'created_at',
    )
    search_fields = ('chat_id', 'first_name', 'last_name', 'username')
    list_filter = (
        'blocked',
        'send_admin_notifications',
        'bot_was_blocked',
        'created_at',
        'is_admin',
        'send_admin_notifications',
    )
    actions = [
        'block_users',
        'unblock_users',
        'refresh_user_data',
        'send_message_action',
    ]
    readonly_fields = (
        'bot_was_blocked',
        'created_at',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("send-message/", self.admin_site.admin_view(self.send_message_view), name="tgbot_telegramuser_send_message"),
            path('<int:object_id>/send_message_user/', self.admin_site.admin_view(self.send_message_user), name='tgbot_telegramuser_send_message_user'),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['send_message_user'] = f"/admin/tgbot/telegramuser/{object_id}/send_message_user/"
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="Заблокировать пользователя(ей)")
    def block_users(self, request, queryset):
        updated = queryset.update(blocked=True)
        self.message_user(
            request,
            f"Заблокировано {updated} пользователь(ей).",
            level=messages.SUCCESS
        )

    @admin.action(description="Разблокировать пользователя(ей)")
    def unblock_users(self, request, queryset):
        updated = queryset.update(blocked=False)
        self.message_user(
            request,
            f"Разблокировано {updated} пользователь(ей).",
            level=messages.SUCCESS
        )

    @admin.action(description="Обновить данные пользователя")
    def refresh_user_data(self, request, queryset):
        from tgbot.user_helper import sync_user_data

        total = queryset.count()
        successes = 0
        errors = []

        for user in queryset:
            try:
                sync_user_data(user)
                successes += 1
            except Exception as e:
                errors.append(f"{user.chat_id}: {e}")

        if successes:
            self.message_user(
                request,
                f"Успешно обновлено данных для {successes} из {total} пользователя(ей).",
                level=messages.SUCCESS
            )
        for err in errors:
            self.message_user(request, f"Ошибка при обновлении пользователя {err}", level=messages.ERROR)

    @admin.action(description="Отправить сообщение выбранным пользователям")
    def send_message_action(self, request, queryset):
        user_ids = ",".join(str(user.id) for user in queryset)
        return redirect(f"{request.path}send-message/?users={user_ids}")

    def process_send_message(self, request, users):
        """
        Обрабатывает форму отправки сообщения для заданного списка пользователей.
        Если POST – выполняет отправку, если GET – отображает форму.
        """
        if request.method == "POST":
            form = SendMessageForm(request.POST)
            if form.is_valid():
                message_text = form.cleaned_data["message"]
                sender = form.cleaned_data["sender"]
                result = mass_mailing(admin=sender, users=users, text=message_text)
                if result is None:
                    result = "Не удалось отправить сообщения"
                messages.success(request, result)
                return redirect("..")
        else:
            form = SendMessageForm()

        return render(request, "admin/send_message.html", {"form": form, "users": users})

    def send_message_user(self, request, object_id):
        user = self.get_object(request, object_id)
        return self.process_send_message(request, [user])

    def send_message_view(self, request):
        user_ids = request.GET.get("users", "")
        user_ids = user_ids.split(",") if user_ids else []
        from tgbot.models import TelegramUser
        users = TelegramUser.objects.filter(id__in=user_ids)
        return self.process_send_message(request, users)


@admin.register(SentMessage)
class SentMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_id', 'telegram_user', 'created_at')
    search_fields = ('message_id', 'telegram_user__chat_id', 'telegram_user__username')
    list_filter = ('telegram_user', 'created_at')
