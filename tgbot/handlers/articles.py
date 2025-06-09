import datetime
from io import BytesIO
from telebot.types import CallbackQuery

from tgbot.logics.apod_api import APODClient, APODClientError
from tgbot.models import ApodFile, ApodApiKey, ArticlesSection, ArticlesSubsection
from tgbot.logics.constants import CallbackData, Messages
from tgbot.dispatcher import get_main_bot
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from tgbot.logics.messages import SendMessages

from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например articles_apod_handlers.py → logs/articles_apod_handlers.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")

@property
def bot():
    return get_main_bot()

# Обработчик для APOD (Astronomy Picture of the Day)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.APOD)
def handle_apod(call: CallbackQuery):
    logger.info("Received APOD callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for APOD call: {}", call.data)
        return
    try:
        logger.debug("Fetching APOD for user {}", user.id)
        api_key = ApodApiKey.objects.filter(active=True).first()
        if not api_key:
            logger.error("No active APOD API key found for APOD request by user {}", user.id)
            SendMessages.APOD.error_no_key(user)
            return
        client = APODClient(api_key.key)
        apod_data = client.fetch_today()
        logger.debug("APOD data fetched: {}", apod_data)
        SendMessages.APOD.send_picture(user, apod_data)
    except APODClientError as e:
        logger.error("APODClientError for user {}: {}", user.id, e)
        SendMessages.APOD.error_fetch(user)
    except Exception as e:
        logger.exception("Unhandled error in handle_apod for user {}", user.id)
        SendMessages.APOD.error_general(user)

# Обработчик для ARTICLES (главное меню статей)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.ARTICLES)
def handle_articles(call: CallbackQuery):
    logger.info("Received ARTICLES callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for ARTICLES call: {}", call.data)
        return
    logger.debug("Sending sections list to user {}", user.id)
    SendMessages.Articles.choose_section(user)

# Обработчик для ARTICLES_SECTION (с параметром section_id)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.ARTICLES_SECTION)
def handle_articles_section(call: CallbackQuery):
    logger.info("Received ARTICLES_SECTION callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for ARTICLES_SECTION call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params for ARTICLES_SECTION: {}", params)
    section_id = extract_int_param(call, params, CallbackData.ARTICLES_SECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if section_id is None:
        logger.error("Missing or invalid ARTICLES_SECTION_ID in params: {}", params)
        return

    try:
        section = ArticlesSection.objects.get(pk=section_id)
        logger.debug("Found section id={} name='{}' for user {}", section.id, section.title, user.id)
    except ArticlesSection.DoesNotExist:
        logger.error("ArticlesSection not found: id={} for user {}", section_id, user.id)
        bot.answer_callback_query(call.id, Messages.NOT_FOUND_ERROR.format(item="Раздел"))
        return

    SendMessages.Articles.choose_subsection(user, section)

# Обработчик для ARTICLES_SUBSECTION (с параметром subsection_id)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.ARTICLES_SUBSECTION)
def handle_articles_subsection(call: CallbackQuery):
    logger.info("Received ARTICLES_SUBSECTION callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for ARTICLES_SUBSECTION call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params for ARTICLES_SUBSECTION: {}", params)
    subsection_id = extract_int_param(call, params, CallbackData.ARTICLES_SUBSECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if subsection_id is None:
        logger.error("Missing or invalid ARTICLES_SUBSECTION_ID in params: {}", params)
        return

    try:
        subsection = ArticlesSubsection.objects.get(pk=subsection_id)
        logger.debug("Found subsection id={} title='{}' for user {}", subsection.id, subsection.title, user.id)
    except ArticlesSubsection.DoesNotExist:
        logger.error("ArticlesSubsection not found: id={} for user {}", subsection_id, user.id)
        bot.answer_callback_query(call.id, Messages.NOT_FOUND_ERROR.format(item="Подраздел"))
        return

    SendMessages.Articles.choose_article(user, subsection)
