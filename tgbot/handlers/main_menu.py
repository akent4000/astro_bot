from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
from tgbot.models import UserQuizSession
bot = get_main_bot()
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from tgbot.logics.messages import SendMessages

# Обработчик для MENU (главное меню)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU)
def main_menu(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    params = extract_query_params(call, False)

    session_to_delete_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_SESSION_DELETE_ID,
    )

    if session_to_delete_id is not None:
        session_to_delete = UserQuizSession.objects.filter(id=session_to_delete_id).first()
        if session_to_delete:
            session_to_delete.delete()
        
    SendMessages.MainMenu.menu(user)

# Обработчик для MENU (главное меню)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.MENU_FORCED_DELETE)
def main_menu_forced_delete(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.MainMenu.menu(user, forced_delete=True)