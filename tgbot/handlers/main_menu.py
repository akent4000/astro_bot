from telebot.types import CallbackQuery
from tgbot.dispatcher import bot
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param
from tgbot.logics.messages import SendMessages

# Обработчик для MENU (главное меню)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.MENU)
def handle_int_facts(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MainMenu.menu(user)