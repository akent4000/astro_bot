import re
import urllib.parse
from telebot.types import CallbackQuery, MessageEntity

from tgbot.dispatcher import get_main_bot
from tgbot.models import *
from tgbot.logics.constants import *
from tgbot.logics.messages import *
from tgbot.logics.keyboards import *

from pathlib import Path
from loguru import logger
from cachetools import TTLCache, cached

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например user_helper.py → logs/user_helper.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

def get_user_from_call(call: CallbackQuery) -> TelegramUser | None:
    """Извлекает пользователя по chat_id из сообщения callback."""
    try:
        return TelegramUser.get_user_by_chat_id(chat_id=call.from_user.id)
    except TelegramUser.DoesNotExist:
        logger.error(f"Пользователь {call.from_user.id} не найден")
        bot.answer_callback_query(call.id, Messages.USER_NOT_FOUND_ERROR)
        return None

def extract_query_params(call: CallbackQuery, show_warning: bool=True) -> dict:
    """Извлекает параметры из callback data."""
    try:
        query_string = call.data.split("?", 1)[1]
        return urllib.parse.parse_qs(query_string)
    except IndexError:
        if show_warning:
            bot = get_main_bot()
            bot.answer_callback_query(call.id, Messages.MISSING_PARAMETERS_ERROR)
        return {}

def extract_int_param(call: CallbackQuery, params: dict, key: str, error_message: str | None=None) -> int | None:
    """Извлекает целочисленный параметр по ключу из словаря параметров."""
    param_list = params.get(key)
    if not param_list:
        if error_message:
            bot = get_main_bot()
            bot.answer_callback_query(call.id, error_message)
        return None
    try:
        return int(param_list[0])
    except ValueError:
        if error_message:
            bot = get_main_bot()
            bot.answer_callback_query(call.id, Messages.INCORRECT_VALUE_ERROR.format(key=key))
        return None

get_callback_name_from_call_cache = TTLCache(maxsize=100, ttl=3)
@cached(get_callback_name_from_call_cache)
def get_callback_name_from_call(call: CallbackQuery):
    return call.data.split("?", 1)[0]