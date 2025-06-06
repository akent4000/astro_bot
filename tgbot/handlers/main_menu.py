from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
bot = get_main_bot()
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from tgbot.logics.messages import SendMessages

# Обработчик для MENU (главное меню)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU)
def handle_int_facts(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MainMenu.menu(user)

# Обработчик для MENU (главное меню)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU_FORCED_DELETE)
def handle_int_facts(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MainMenu.menu(user, forced_delete=True)