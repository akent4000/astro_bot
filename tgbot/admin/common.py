# tgbot/admin/common.py

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

# Заголовки админки
admin.site.site_header = "Администрирование Astro Bot"
admin.site.site_title = "Администрирование Astro Bot"
admin.site.index_title = "Администрирование Astro Bot"
