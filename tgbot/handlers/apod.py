import datetime
from io import BytesIO
from telebot.types import CallbackQuery

from tgbot.logics.apod_api import APODClient, APODClientError
from tgbot.models import ApodFile, ApodApiKey
from tgbot.logics.constants import CallbackData
from tgbot.dispatcher import bot 
from tgbot.logics.user_helper import get_user_from_call
from tgbot.logics.messages import SendMessages


# Обработчик для APOD
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.APOD)
def handle_apod(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    SendMessages.Apod.send_apod(user)
