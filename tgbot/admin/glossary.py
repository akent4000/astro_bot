# tgbot/admin/glossary.py

from django.contrib import admin
from solo.admin import SingletonModelAdmin

from tgbot.models import Glossary


@admin.register(Glossary)
class GlossaryAdmin(SingletonModelAdmin):
    fieldsets = (
        (None, {'fields': ('link',)}),
    )
