import datetime
from io import BytesIO
from telebot.types import CallbackQuery

from tgbot.logics.apod_api import APODClient, APODClientError
from tgbot.models import ApodFile, ApodApiKey
from tgbot.logics.constants import CallbackData, Messages
from tgbot.dispatcher import get_main_bot
from tgbot.logics.user_helper import get_user_from_call, get_callback_name_from_call
from tgbot.logics.messages import SendMessages
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Настройка логирования для данного модуля
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(
    str(log_filename),
    rotation="10 MB",
    level="DEBUG",
    backtrace=True,
    diagnose=True,
)

def bot():
    return get_main_bot()

bot().callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.APOD)
def handle_apod(call: CallbackQuery):
    logger.info("Received APOD callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for APOD callback: {}", call.data)
        return

    try:
        logger.debug("Invoking SendMessages.Apod.send_apod for user {}", user.id)
        SendMessages.Apod.send_apod(user)
        logger.info("APOD sent successfully to user {}", user.id)
    except APODClientError as e:
        logger.error("APODClientError when sending APOD to user {}: {}", user.id, e)
        SendMessages.Apod.error_fetch(user)
    except Exception:
        logger.exception("Unexpected error in handle_apod for user {}", user.id)
        SendMessages.Apod.error_general(user)