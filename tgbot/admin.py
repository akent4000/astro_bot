import base64
import io
import os
import secrets
import string
import zipfile

import telebot
from django import forms
from django.contrib import admin, messages
from django.db.models import Count, IntegerField, Q, Value
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode

from rangefilter.filters import DateRangeFilter, NumericRangeFilter

from solo.admin import SingletonModelAdmin

from tgbot.managers.ssh_manager import SSHAccessManager, sync_keys
from tgbot.models import *
from tgbot.forms import SSHKeyAdminForm, SSHKeyChangeForm, SendMessageForm

admin.site.site_header = "Администрирование Astro Bot"
admin.site.site_title = "Администрирование Astro Bot"
admin.site.index_title = "Администрирование Astro Bot"

##############################
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
# Server Admin (Singleton)
##############################
class ServerAdminForm(forms.ModelForm):
    PERMIT_ROOT_LOGIN_CHOICES = [
        ('yes', 'Полный доступ'),
        ('no', 'Доступ запрещён'),
        ('prohibit-password', 'Только без пароля (например с SSH ключом)'),
        ('forced-commands-only', 'Только принудительные команды'),
    ]
    permit_root_login = forms.ChoiceField(
        choices=PERMIT_ROOT_LOGIN_CHOICES,
        initial='prohibit-password',
        label="root логин"
    )
    
    class Meta:
        model = Server
        fields = '__all__'

@admin.register(Server)
class ServerAdmin(SingletonModelAdmin):
    form = ServerAdminForm
    actions = ['sync_ssh_keys']
    fieldsets = (
        (None, {'fields': ('ip',)}),
        ('Настройки сервера', {'fields': ('user',)}),
        ('SSH аутентификация', {'fields': ('password_auth', 'pubkey_auth', 'permit_empty_passwords', 'permit_root_login')}),
    )

    @admin.action(description="Синхронизировать SSH ключи")
    def sync_ssh_keys(self, request, queryset=None):
        server = Server.get_solo()
        sync_keys()
        self.message_user(request, f"SSH ключи синхронизированы для сервера {server.ip}.", level=messages.SUCCESS)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'sync-ssh-keys/',
                self.admin_site.admin_view(self.sync_ssh_keys),
                name='server_sync_ssh_keys'
            ),
            path(
                'reset-password/',
                self.admin_site.admin_view(self.reset_password),
                name='server_reset_password'
            ),
        ]
        return custom_urls + urls

    def reset_password(self, request):
        server = Server.get_solo()
        alphabet = string.ascii_letters + string.digits
        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        new_password_for_user = (server.user, new_password)
        manager = SSHAccessManager()
        manager.set_auth_methods(
            server.password_auth,
            server.pubkey_auth,
            server.permit_root_login,
            server.permit_empty_passwords,
            new_password_for_user
        )
        self.message_user(request, f"Пароль для пользователя {server.user} сброшен. Новый пароль: {new_password}", level=messages.SUCCESS)
        return HttpResponseRedirect(request.path)

##############################
# SSHKey Admin
##############################
@admin.register(SSHKey)
class SSHKeyAdmin(admin.ModelAdmin):
    list_display = ("key_name", "public_key", "created_at")
    readonly_fields = ("public_key", "created_at")
    form = SSHKeyAdminForm

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'sync-keys/',
                self.admin_site.admin_view(self.sync_keys),
                name="%s_%s_sync_keys" % (self.model._meta.app_label, self.model._meta.model_name)
            ),
            path(
                'delete-key/<int:pk>/',
                self.admin_site.admin_view(self.delete_key),
                name="sshkey_delete_key"
            ),
        ]
        return custom_urls + urls

    def sync_keys(self, request):
        sync_keys()
        self.message_user(request, "SSH ключи успешно синхронизированы.", messages.SUCCESS)
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        sync_url = reverse("admin:%s_%s_sync_keys" % (self.model._meta.app_label, self.model._meta.model_name))
        extra_context["sync_keys_url"] = sync_url
        return super().changelist_view(request, extra_context=extra_context)

    def delete_key(self, request, pk):
        obj = self.get_object(request, pk)
        if obj:
            obj.delete()
            self.message_user(request, "SSH ключ удалён.", level=messages.SUCCESS)
        else:
            self.message_user(request, "SSH ключ не найден.", level=messages.ERROR)
        return redirect("..")

    def save_model(self, request, obj, form, change):
        if not change:
            manager = SSHAccessManager()
            comment = obj.key_name
            passphrase = form.cleaned_data.get("passphrase", "")
            key_type = form.cleaned_data.get("key_type", "rsa")
            bits = form.cleaned_data.get("bits") or 2048

            result = manager.generate_ssh_key(comment=comment, passphrase=passphrase, key_type=key_type, bits=bits)
            if result is None:
                messages.error(request, "Ошибка генерации SSH ключа.")
                return
            obj.public_key = result["public_key"]
            super().save_model(request, obj, form, change)
            obj._private_key = result["private_key"]
        else:
            super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        if hasattr(obj, "_private_key"):
            pem_filename = f"{obj.key_name}_private_key.pem"
            zip_filename = f"{obj.key_name}_private_key.zip"
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                zip_info = zipfile.ZipInfo(pem_filename)
                zip_info.external_attr = (0o600 << 16)
                zip_file.writestr(zip_info, obj._private_key)
            zip_buffer.seek(0)
            zip_content = zip_buffer.getvalue()
            zip_content_b64 = base64.b64encode(zip_content).decode('utf-8')
            
            changelist_url = reverse("admin:%s_%s_changelist" % (obj._meta.app_label, obj._meta.model_name))
            
            html = f"""
            <html>
            <head>
                <script>
                function downloadAndRedirect() {{
                    var a = document.createElement('a');
                    a.href = "data:application/zip;base64,{zip_content_b64}";
                    a.download = "{zip_filename}";
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(function() {{
                        window.location.href = "{changelist_url}";
                    }}, 1000);
                }}
                window.onload = downloadAndRedirect;
                </script>
            </head>
            <body>
                <p>SSH ключ успешно создан. Если скачивание не началось автоматически, <a href="#" onclick="downloadAndRedirect(); return false;">нажмите здесь</a>.</p>
            </body>
            </html>
            """
            del obj._private_key
            return HttpResponse(html)
        return super().response_add(request, obj, post_url_continue)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("key_name", "public_key", "created_at")
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            kwargs["form"] = SSHKeyChangeForm
        else:
            kwargs["form"] = SSHKeyAdminForm
        return super().get_form(request, obj, **kwargs)

##############################
# Configuration Admin (Singleton)
##############################
@admin.register(Configuration)
class ConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        (None, {'fields': ('test_mode',)}),
    )



##############################
# TelegramUser Admin
##############################
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
            path("send-message/", self.admin_site.admin_view(self.send_message_view), name="send_message"),
            path('<int:object_id>/send_message_user/', self.admin_site.admin_view(self.send_message_user), name='telegramuser_send_message_user'),
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
        """
        Для каждого выбранного TelegramUser вызывает sync_user_data(user).
        Логирует успехи и ошибки через сообщения в админке.
        """
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
        if errors:
            for err in errors:
                self.message_user(
                    request,
                    f"Ошибка при обновлении пользователя {err}",
                    level=messages.ERROR
                )
    @admin.action(description="Отправить сообщение выбранным пользователям")
    def send_message_action(self, request, queryset):
        user_ids = ",".join(str(user.id) for user in queryset)
        return redirect(f"{request.path}send-message/?users={user_ids}")
    
    def process_send_message(self, request, users):
        """
        Обрабатывает форму отправки сообщения для заданного списка пользователей.
        Если POST – выполняет отправку, если GET – отображает форму.
        """
        from tgbot.logics.administrator_actions import mass_mailing
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
        """
        Обработчик для отправки сообщения конкретному пользователю (на странице change).
        """
        user = self.get_object(request, object_id)
        return self.process_send_message(request, [user])


    def send_message_view(self, request):
        """
        Обработчик для отправки сообщения группе пользователей.
        Пользовательские id передаются через GET-параметр "users" в виде строки через запятую.
        """
        user_ids = request.GET.get("users", "")
        # Если параметр пустой, создаём пустой список, иначе разделяем по запятой
        user_ids = user_ids.split(",") if user_ids else []
        users = TelegramUser.objects.filter(id__in=user_ids)
        return self.process_send_message(request, users)


##############################
# SentMessage Admin
##############################
@admin.register(SentMessage)
class SentMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_id', 'telegram_user', 'created_at')
    search_fields = ('message_id', 'telegram_user__chat_id', 'telegram_user__username')
    list_filter = ('telegram_user', 'created_at')
