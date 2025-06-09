import datetime
from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from tgbot.logics.messages import SendMessages
from tgbot.models import TelegramUser
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например moon_calc.py → logs/moon_calc_handlers.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")

def bot():
    return get_main_bot()

# Обработчик для MOON_CALC (главное меню MoonCalc)
bot().callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MOON_CALC)
def handle_moon_calc(call: CallbackQuery):
    logger.info("Received MOON_CALC callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for MOON_CALC call: {}", call.data)
        return
    logger.debug("Sending MoonCalc menu to user {}", user.id)
    SendMessages.MoonCalc.menu(user)

# Обработчик для MOON_CALC_TODAY
bot().callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MOON_CALC_TODAY)
def handle_moon_calc_today(call: CallbackQuery):
    logger.info("Received MOON_CALC_TODAY callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for MOON_CALC_TODAY call: {}", call.data)
        return
    logger.debug("Sending today's moon data to user {}", user.id)
    SendMessages.MoonCalc.today(user)

# Обработчик для MOON_CALC_ENTER_DATE
bot().callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MOON_CALC_ENTER_DATE)
def handle_moon_calc_enter_date(call: CallbackQuery):
    logger.info("Received MOON_CALC_ENTER_DATE callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for MOON_CALC_ENTER_DATE call: {}", call.data)
        return
    logger.debug("Prompting user {} to enter date", user.id)
    sent = SendMessages.MoonCalc.enter_date(user)
    bot.register_next_step_handler(sent, process_moon_date, user)


def process_moon_date(message, user: TelegramUser):
    """
    Обрабатывает ответ пользователя на запрос даты.
    Парсит дату и вызывает SendMessages.MoonCalc.date.
    Если формат некорректный, просит ввести снова.
    """
    text = message.text.strip()
    logger.info("User {} entered date text: '{}'", user.id, text)
    try:
        # Парсим строку в datetime; при неверном формате выбросит ValueError
        dt = datetime.datetime.strptime(text, "%d.%m.%Y")
        logger.debug("Parsed date {} for user {}", dt, user.id)
    except ValueError:
        logger.error("Failed to parse date '{}' for user {}", text, user.id)
        sent = SendMessages.MoonCalc.incorrect_enter_date(user)
        logger.debug("Prompting user {} to re-enter date", user.id)
        bot.register_next_step_handler(sent, process_moon_date, user)
        return

    logger.info("Processing moon data for user {} on date {}", user.id, dt)
    SendMessages.MoonCalc.date(user, dt)
