# tgbot/admin/server.py

import secrets
import string
from django import forms
from django.contrib import admin, messages
from django.urls import path
from django.http import HttpResponseRedirect

from solo.admin import SingletonModelAdmin
from tgbot.models import Server
from tgbot.managers.ssh_manager import SSHAccessManager, sync_keys

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
        ('SSH аутентификация', {'fields': (
            'password_auth',
            'pubkey_auth',
            'permit_empty_passwords',
            'permit_root_login'
        )}),
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
                name='tgbot_server_sync_ssh_keys'
            ),
            path(
                'reset-password/',
                self.admin_site.admin_view(self.reset_password),
                name='tgbot_server_reset_password'
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
