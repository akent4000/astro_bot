from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
bot = get_main_bot()
from tgbot.logics.constants import CallbackData, Messages
from tgbot.models import ArticlesSection, ArticlesSubsection, QuizTopic, QuizLevel, Quiz
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param

def getCallbackNameFromCall(call: CallbackQuery):
    return call.data.split("?", 1)[0]


# Обработчик для QUIZZES (главное меню квизов)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.QUIZZES)
def handle_quizzes(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отображения списка тем квизов

# Обработчик для QUIZZES_TOPIC (с параметром topic_id)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.QUIZZES_TOPIC)
def handle_quizzes_topic(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    topic_id = extract_int_param(call, params, CallbackData.QUIZZES_TOPIC_ID, Messages.MISSING_PARAMETERS_ERROR)
    if topic_id is None:
        return

    # Здесь можно получить объект темы:
    # topic = QuizTopic.objects.filter(id=topic_id).first()
    # И далее — логика для отображения уровней

# Обработчик для QUIZZES_LEVEL (с параметрами level_id и topic_id)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.QUIZZES_LEVEL)
def handle_quizzes_level(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    level_id = extract_int_param(call, params, CallbackData.QUIZZES_LEVEL_ID, Messages.MISSING_PARAMETERS_ERROR)
    if level_id is None:
        return
    topic_id = extract_int_param(call, params, CallbackData.QUIZZES_TOPIC_ID, Messages.MISSING_PARAMETERS_ERROR)
    if topic_id is None:
        return

    # Можно получить объекты:
    # level = QuizLevel.objects.filter(id=level_id).first()
    # topic = QuizTopic.objects.filter(id=topic_id).first()
    # И далее — логика для отображения списка квизов

# Обработчик для QUIZZES_QUIZ (с параметром quiz_id)
@bot.callback_query_handler(func=lambda call: getCallbackNameFromCall(call) == CallbackData.QUIZZES_QUIZ)
def handle_quizzes_quiz(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    quiz_id = extract_int_param(call, params, CallbackData.QUIZZES_QUIZ_ID, Messages.MISSING_PARAMETERS_ERROR)
    if quiz_id is None:
        return

    # Здесь можно получить объект Quiz:
    # quiz = Quiz.objects.filter(id=quiz_id).first()
    # И дальше — отправка самого теста или вопросов
