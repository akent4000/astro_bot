from telebot.types import CallbackQuery
from tgbot.dispatcher import bot
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param

# Обработчик для MOON_CALC (главное меню MoonCalc)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.MOON_CALC)
def handle_moon_calc(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    

# Обработчик для MOON_CALC_TODAY
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.MOON_CALC_TODAY)
def handle_moon_calc_today(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для расчёта фазы Луны на сегодня

# Обработчик для MOON_CALC_ENTER_DATE
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.MOON_CALC_ENTER_DATE)
def handle_moon_calc_enter_date(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для запроса даты у пользователя

