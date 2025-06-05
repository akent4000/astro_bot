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
                # Получаем все message_id, которые храним в базе
                ids_qs = SentMessage.objects.filter(telegram_user=user)
                message_ids = list(ids_qs.values_list("message_id", flat=True))

                # Пробуем удалить их у Telegram
                bot.delete_messages(user.chat_id, message_ids)

                # После успешного (или даже неудачного) удаления убираем записи из базы
                ids_qs.delete()
            except Exception:
                # Если что-то пошло не так, всё равно очищаем записи из базы,
                # чтобы не накапливались "битые" ссылки на сообщения
                SentMessage.objects.filter(telegram_user=user).delete()

        SendMessages.MainMenu.menu(user)

    except Exception as e:
        logger.exception(e)
