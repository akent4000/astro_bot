import datetime
from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
bot = get_main_bot()
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param
from tgbot.logics.messages import SendMessages
from tgbot.models import TelegramUser
from tgbot.handlers.utils import getCallbackNameFromCall

# Обработчик для MOON_CALC (главное меню MoonCalc)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.MOON_CALC)
def handle_moon_calc(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MoonCalc.menu(user)

# Обработчик для MOON_CALC_TODAY
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.MOON_CALC_TODAY)
def handle_moon_calc_today(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MoonCalc.today(user)


# Обработчик для MOON_CALC_ENTER_DATE
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.MOON_CALC_ENTER_DATE)
def handle_moon_calc_enter_date(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    sent = SendMessages.MoonCalc.enter_date(user)
    bot.register_next_step_handler(sent, process_moon_date, user)


def process_moon_date(message, user: TelegramUser):
    """
    Обрабатывает ответ пользователя на запрос даты.
    Парсит дату и вызывает SendMessages.MoonCalc.date.
    Если формат некорректный, просит ввести снова.
    """
    text = message.text.strip()
    try:
        # Парсим строку в datetime; при неверном формате выбросит ValueError
        dt = datetime.datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        # Неправильный формат, просим ещё раз
        sent = SendMessages.MoonCalc.incorrect_enter_date(user)
        bot.register_next_step_handler(sent, process_moon_date, user)
        return

    # Дата получена и распарсена, вызываем нужный метод
    SendMessages.MoonCalc.date(user, dt)
