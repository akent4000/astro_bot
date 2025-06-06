# tgbot/admin/ssh_key.py

import base64
import io
import zipfile

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.http import HttpResponse

from tgbot.managers.ssh_manager import sync_keys, SSHAccessManager
from tgbot.models import SSHKey
from tgbot.forms import SSHKeyAdminForm, SSHKeyChangeForm


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
