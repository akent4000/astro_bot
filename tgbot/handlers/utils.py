from telebot.types import CallbackQuery
from tgbot.dispatcher import bot
from tgbot.logics.constants import CallbackData, Messages
from tgbot.models import ArticlesSection, ArticlesSubsection, QuizTopic, QuizLevel, Quiz
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param



# Обработчик для INT_FACTS (главное меню IntFacts)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS)
def handle_int_facts(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отображения меню IntFacts

# Обработчик для INT_FACTS_TODAY
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS_TODAY)
def handle_int_facts_today(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отправки факта на сегодня

# Обработчик для INT_FACTS_SUB
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS_SUB)
def handle_int_facts_sub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для подписки на рассылку фактов

# Обработчик для INT_FACTS_UNSUB
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS_UNSUB)
def handle_int_facts_unsub(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отписки от рассылки фактов

# Обработчик для INT_FACTS_DEFAULT_TIME
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS_DEFAULT_TIME)
def handle_int_facts_default_time(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для установки времени по умолчанию

# Обработчик для INT_FACTS_ENTER_TIME
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.INT_FACTS_ENTER_TIME)
def handle_int_facts_enter_time(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для запроса времени у пользователя

# Обработчик для APOD
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.APOD)
def handle_apod(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отправки сегодняшнего APOD

# Обработчик для ARTICLES (главное меню статей)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.ARTICLES)
def handle_articles(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отображения списка разделов статей

# Обработчик для ARTICLES_SECTION (с параметром section_id)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.ARTICLES_SECTION)
def handle_articles_section(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    section_id = extract_int_param(call, params, CallbackData.ARTICLES_SECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if section_id is None:
        return

    # Здесь можно получить объект раздела:
    # section = ArticlesSection.objects.filter(id=section_id).first()
    # И дальше — логика для отображения подразделов

# Обработчик для ARTICLES_SUBSECTION (с параметром subsection_id)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.ARTICLES_SUBSECTION)
def handle_articles_subsection(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    subsection_id = extract_int_param(call, params, CallbackData.ARTICLES_SUBSECTION_ID, Messages.MISSING_PARAMETERS_ERROR)
    if subsection_id is None:
        return

    # Здесь можно получить объект подраздела:
    # subsection = ArticlesSubsection.objects.filter(id=subsection_id).first()
    # И дальше — логика для отображения списка статей

# Обработчик для ARTICLES_ARTICLE (с параметром article_id)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.ARTICLES_ARTICLE)
def handle_articles_article(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    article_id = extract_int_param(call, params, CallbackData.ARTICLES_ARTICLE_ID, Messages.MISSING_PARAMETERS_ERROR)
    if article_id is None:
        return

    # Здесь можно получить объект статьи:
    # article = Article.objects.filter(id=article_id).first()
    # И дальше — логика для отправки самой статьи или ссылки

# Обработчик для QUIZZES (главное меню квизов)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.QUIZZES)
def handle_quizzes(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    # Логика для отображения списка тем квизов

# Обработчик для QUIZZES_TOPIC (с параметром topic_id)
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.QUIZZES_TOPIC)
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
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.QUIZZES_LEVEL)
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
@bot.callback_query_handler(func=lambda call: call.data.split("?", 1)[0] == CallbackData.QUIZZES_QUIZ)
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
