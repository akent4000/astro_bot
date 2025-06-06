from telebot.types import CallbackQuery
from tgbot.dispatcher import bot
from tgbot.logics.constants import CallbackData, Messages
from tgbot.logics.messages import SendMessages
from tgbot.models import ArticlesSection, ArticlesSubsection, QuizTopic, QuizLevel, Quiz
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param
from tgbot.handlers.utils import getCallbackNameFromCall

# Обработчик для INT_FACTS (главное меню IntFacts)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS)
def handle_int_facts(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.IntFacts.menu(user)

# Обработчик для INT_FACTS_TODAY
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_TODAY)
def handle_int_facts_today(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отправки факта на сегодня

# Обработчик для INT_FACTS_SUB
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_SUB)
def handle_int_facts_sub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для подписки на рассылку фактов

# Обработчик для INT_FACTS_UNSUB
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_UNSUB)
def handle_int_facts_unsub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отписки от рассылки фактов