import datetime
from typing import Union
from telebot.types import CallbackQuery, Message
from tgbot.dispatcher import get_main_bot
from tgbot.logics.constants import ButtonNames, CallbackData, Messages
from tgbot.logics.messages import SendMessages
from tgbot.models import ArticlesSection, ArticlesSubsection, DailySubscription, QuizTopic, QuizLevel, Quiz, TelegramUser
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")

bot = get_main_bot()

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS)
def handle_int_facts(call: CallbackQuery):
    logger.info("Received INT_FACTS callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS call: {}", call.data)
        return
    logger.debug("Sending IntFacts menu to user {}", user.id)
    SendMessages.IntFacts.menu(user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS_TODAY)
def handle_int_facts_today(call: CallbackQuery):
    logger.info("Received INT_FACTS_TODAY callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS_TODAY call: {}", call.data)
        return
    logger.debug("Sending today's fact to user {}", user.id)
    SendMessages.IntFacts.today(user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS_SUB)
def handle_int_facts_sub(call: CallbackQuery):
    logger.info("Received INT_FACTS_SUB callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS_SUB call: {}", call.data)
        return
    logger.debug("Prompting user {} to choose subscription time or default", user.id)
    SendMessages.IntFacts.choose_time_or_default(user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS_UNSUB)
def handle_int_facts_unsub(call: CallbackQuery):
    logger.info("Received INT_FACTS_UNSUB callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS_UNSUB call: {}", call.data)
        return
    subscriptions = DailySubscription.objects.filter(user=user)
    count = subscriptions.count()
    if count > 0:
        subscriptions.delete()
        logger.info("Deleted {} DailySubscription entries for user {}", count, user.id)
    else:
        logger.debug("No DailySubscription entries found for user {} to delete", user.id)
    SendMessages.IntFacts.unsub(user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS_DEFAULT_TIME)
def handle_int_facts_default_time(call: CallbackQuery):
    logger.info("Received INT_FACTS_DEFAULT_TIME callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS_DEFAULT_TIME call: {}", call.data)
        return
    logger.debug("Using default subscription time for user {}", user.id)
    process_int_facts_time_sub(ButtonNames.INT_FACTS_DEFAULT_TIME, user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.INT_FACTS_ENTER_TIME)
def handle_int_facts_enter_time(call: CallbackQuery):
    logger.info("Received INT_FACTS_ENTER_TIME callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for INT_FACTS_ENTER_TIME call: {}", call.data)
        return
    logger.debug("Prompting user {} to enter custom time", user.id)
    sent = SendMessages.IntFacts.enter_time(user)
    bot.register_next_step_handler(sent, process_int_facts_time_sub, user)


def process_int_facts_time_sub(input_data: Union[str, Message], user: TelegramUser):
    # Получаем текст из Message или из переданной строки
    if isinstance(input_data, Message):
        text = input_data.text.strip()
    else:
        text = input_data.strip()
    logger.info("User {} provided time input: {}", user.id, text)
    try:
        selected_time = datetime.datetime.strptime(text, "%H:%M").time()
        logger.debug("Parsed time {} for user {}", selected_time, user.id)
    except ValueError:
        logger.error("Failed to parse time '{}' for user {}", text, user.id)
        sent = SendMessages.IntFacts.incorrect_enter_time(user)
        logger.debug("Prompting user {} to re-enter time", user.id)
        bot.register_next_step_handler(sent, process_int_facts_time_sub, user)
        return

    # Создаём или обновляем подписку
    try:
        subscription = user.daily_subscription
        subscription.send_time = selected_time
        subscription.save(update_fields=["send_time"])
        logger.info("Updated DailySubscription for user {} to time {}", user.id, selected_time)
    except DailySubscription.DoesNotExist:
        DailySubscription.objects.create(user=user, send_time=selected_time)
        logger.info("Created new DailySubscription for user {} at time {}", user.id, selected_time)

    logger.debug("Notifying user {} about successful subscription", user.id)
    SendMessages.IntFacts.sub(user, selected_time)
