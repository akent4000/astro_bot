from django.urls import path
from tgbot.views import telegram_webhook
from tgbot.logics.constants import Constants
app_name = 'tgbot'

urlpatterns = [
    path(f'{Constants.WEBHOOCK}/<int:hook_id>/', telegram_webhook, name='telegram_webhook'),
]
