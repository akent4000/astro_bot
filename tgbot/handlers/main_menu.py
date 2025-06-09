from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
from tgbot.models import UserQuizSession
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from tgbot.logics.messages import SendMessages
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например main_menu_handlers.py → logs/main_menu_handlers.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")

bot = get_main_bot()

# Обработчик для главного меню
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU)
def main_menu(call: CallbackQuery):
    logger.info("Received MENU callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for MENU call: {}", call.data)
        return

    params = extract_query_params(call, False)
    logger.debug("Extracted params for MENU: {}", params)

    session_to_delete_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_SESSION_DELETE_ID,
    )
    if session_to_delete_id is not None:
        logger.debug("Attempting to delete session id {} for user {}", session_to_delete_id, user.id)
        session_to_delete = UserQuizSession.objects.filter(id=session_to_delete_id).first()
        if session_to_delete:
            session_to_delete.delete()
            logger.info("Deleted quiz session {} for user {}", session_to_delete_id, user.id)
        else:
            logger.warning("No session found to delete: id={} for user {}", session_to_delete_id, user.id)

    logger.debug("Sending main menu to user {}", user.id)
    SendMessages.MainMenu.menu(user)

# Обработчик для принудительного удаления сессии и показа меню
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU_FORCED_DELETE)
def main_menu_forced_delete(call: CallbackQuery):
    logger.info("Received MENU_FORCED_DELETE callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for MENU_FORCED_DELETE call: {}", call.data)
        return

    logger.debug("Sending main menu with forced_delete=True to user {}", user.id)
    SendMessages.MainMenu.menu(user, forced_delete=True)