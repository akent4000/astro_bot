import datetime
from io import BytesIO
from telebot.types import CallbackQuery

from tgbot.handlers.utils import getCallbackNameFromCall
from tgbot.logics.apod_api import APODClient, APODClientError
from tgbot.models import ApodFile, ApodApiKey, ArticlesSection, ArticlesSubsection
from tgbot.logics.constants import CallbackData, Messages
from tgbot.dispatcher import bot 
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param

from tgbot.logics.messages import SendMessages

# Обработчик для ARTICLES (главное меню статей)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.ARTICLES)
def handle_articles(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.Articles.choose_section(user)

# Обработчик для ARTICLES_SECTION (с параметром section_id)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.ARTICLES_SECTION)
def handle_articles_section(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    section_id = extract_int_param(call, params, CallbackData.ARTICLES_SECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if section_id is None:
        return

    # Безопасно получаем раздел
    try:
        section = ArticlesSection.objects.get(pk=section_id)
    except ArticlesSection.DoesNotExist:
        bot.answer_callback_query(call.id, Messages.NOT_FOUND_ERROR.format(item="Раздел"))
        return

    SendMessages.Articles.choose_subsection(user, section)


# Обработчик для ARTICLES_SUBSECTION (с параметром subsection_id)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.ARTICLES_SUBSECTION)
def handle_articles_subsection(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    subsection_id = extract_int_param(call, params, CallbackData.ARTICLES_SUBSECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if subsection_id is None:
        return

    # Безопасно получаем подраздел
    try:
        subsection = ArticlesSubsection.objects.get(pk=subsection_id)
    except ArticlesSubsection.DoesNotExist:
        bot.answer_callback_query(call.id, Messages.NOT_FOUND_ERROR.format(item="Подраздел"))
        return

    SendMessages.Articles.choose_article(user, subsection)