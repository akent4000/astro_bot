from telebot.types import Message
from tgbot.dispatcher import get_main_bot
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Commands
from tgbot.logics.keyboards import Keyboards
from tgbot.user_helper import sync_user_data
from tgbot.models import SentMessage
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Настройка логирования для данного модуля
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG", backtrace=True, diagnose=True)

bot = get_main_bot()


@bot.message_handler(commands=[Commands.START])
def handle_start(message: Message):
    logger.info("Received START command from chat_id={}", message.chat.id)
    logger.debug("Message details: chat: {}, from_user: {}, text: {}",
                 message.chat, message.from_user, message.text)
    try:
        # Синхронизация данных пользователя
        user, created = sync_user_data(message)
        logger.info("sync_user_data result for chat_id={}: created={}", message.chat.id, created)

        # Отправка главного меню
        logger.debug("Sending main menu to user_id={}, forced_delete=True", user.id)
        SendMessages.MainMenu.menu(user, forced_delete=True)

    except Exception:
        logger.exception("Error in handle_start for chat_id={}", message.chat.id)
