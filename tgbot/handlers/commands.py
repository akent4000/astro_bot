from telebot.types import Message
from tgbot.dispatcher import bot
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Commands
from tgbot.logics.keyboards import Keyboards
from tgbot.user_helper import sync_user_data
from tgbot.models import SentMessage
from pathlib import Path
from loguru import logger

Path("logs").mkdir(parents=True, exist_ok=True)

log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

@bot.message_handler(commands=[Commands.START])
def handle_start(message: Message):
    try:
        logger.info(f"User {message.chat.id} started the bot.")
        user, created = sync_user_data(message)
        logger.info(f"User {user} created: {created}")
        if not created:
            try:
                ids = SentMessage.objects.filter(telegram_user=user) \
                         .values_list("message_id", flat=True)
                bot.delete_messages(user.chat_id, list(ids))
            except:
                pass
        
        SendMessages.MainMenu.menu(user)

    except Exception as e:
        logger.exception(e)
