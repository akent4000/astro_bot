import datetime
from typing import Union
from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
bot = get_main_bot()
from tgbot.logics.constants import ButtonNames, CallbackData, Messages
from tgbot.logics.messages import SendMessages
from tgbot.models import ArticlesSection, ArticlesSubsection, DailySubscription, QuizTopic, QuizLevel, Quiz, TelegramUser
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param
from tgbot.handlers.utils import getCallbackNameFromCall
from telebot.types import Message

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
    SendMessages.IntFacts.today(user)

# Обработчик для INT_FACTS_SUB
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_SUB)
def handle_int_facts_sub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.IntFacts.choose_time_or_default(user)

# Обработчик для INT_FACTS_UNSUB
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_UNSUB)
def handle_int_facts_unsub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    subscriptions = DailySubscription.objects.filter(user=user)
    if subscriptions.exists():
        subscriptions.delete()
    SendMessages.IntFacts.unsub(user)

# Обработчик для INT_FACTS_DEFAULT_TIME
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_DEFAULT_TIME)
def handle_int_facts_default_time(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    process_int_facts_time_sub(ButtonNames.INT_FACTS_DEFAULT_TIME, user)

# Обработчик для INT_FACTS_ENTER_TIME
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.INT_FACTS_ENTER_TIME)
def handle_int_facts_enter_time(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    sent = SendMessages.IntFacts.enter_time(user)
    bot.register_next_step_handler(sent, process_int_facts_time_sub, user)

def process_int_facts_time_sub(input_data: Union[str, Message], user: TelegramUser):
    """
    Обрабатывает ввод времени для подписки на интересные факты.
    Принимает либо объект Message, либо строку.
    Создаёт новую или обновляет существующую DailySubscription.
    """
    # Получаем текст из Message или из переданной строки
    if isinstance(input_data, Message):
        text = input_data.text.strip()
    else:
        text = input_data.strip()

    try:
        # Парсим строку в datetime.time; при неверном формате выбросит ValueError
        selected_time = datetime.datetime.strptime(text, "%H:%M").time()
    except ValueError:
        # Неправильный формат, просим ввести снова
        sent = SendMessages.IntFacts.incorrect_enter_time(user)
        bot.register_next_step_handler(sent, process_int_facts_time_sub, user)
        return

    # Время распарсено, создаём или обновляем подписку
    try:
        subscription = user.daily_subscription
        subscription.send_time = selected_time
        subscription.save(update_fields=["send_time"])
        selected_time.strftime('%H:%M')
    except DailySubscription.DoesNotExist:
        DailySubscription.objects.create(user=user, send_time=selected_time)
        
    SendMessages.IntFacts.sub(user, selected_time)