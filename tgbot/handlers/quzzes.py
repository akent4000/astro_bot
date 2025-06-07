from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import CallbackData, Messages
from tgbot.models import ArticlesSection, ArticlesSubsection, Choice, QuizTopic, QuizLevel, Quiz, UserQuizAnswer, UserQuizSession
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call

bot = get_main_bot()

# Обработчик для QUIZZES (главное меню квизов)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES)
def handle_quizzes(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return
    SendMessages.Quizzes.choose_topic(user)

# Обработчик для QUIZZES_TOPIC (с параметром topic_id)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_TOPIC)
def handle_quizzes_topic(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    topic_id = extract_int_param(call, params, CallbackData.QUIZZES_TOPIC_ID, Messages.MISSING_PARAMETERS_ERROR)
    if topic_id is None:
        return

    # Получаем объект темы
    topic = QuizTopic.objects.filter(id=topic_id).first()
    if not topic:
        return

    # Отправляем выбор уровня для темы
    SendMessages.Quizzes.choose_level(user, topic)

# Обработчик для QUIZZES_LEVEL (с параметрами level_id и topic_id)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_LEVEL)
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

    # Получаем объекты уровня и темы
    level = QuizLevel.objects.filter(id=level_id).first()
    topic = QuizTopic.objects.filter(id=topic_id).first()
    if not level or not topic:
        return

    # Отправляем выбор квиза для выбранного уровня и темы
    SendMessages.Quizzes.choose_quiz(user, topic, level)

# Обработчик для QUIZZES_QUIZ (с параметром quiz_id)
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_QUIZ)
def handle_quizzes_quiz(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)
    quiz_id = extract_int_param(call, params, CallbackData.QUIZZES_QUIZ_ID, Messages.MISSING_PARAMETERS_ERROR)
    if quiz_id is None:
        return

    quiz = Quiz.objects.filter(id=quiz_id).first()
    if not quiz:
        return    

    question = quiz.questions.order_by("order").first()
    if not question:
        return
    
    session = UserQuizSession.objects.create(user=user, quiz=quiz)
    SendMessages.Quizzes.question(user, question, session)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_QUIZZ_QUESTION_CHOISE)
def handle_quizzes_question_choice(call: CallbackQuery):
    user = get_user_from_call(call)
    if not user:
        return

    params = extract_query_params(call)

    choice_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_QUESTION_CHOISE_ID,
        Messages.MISSING_PARAMETERS_ERROR
    )
    if choice_id is None:
        return

    session_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_SESSION_ID,
        Messages.MISSING_PARAMETERS_ERROR
    )
    if session_id is None:
        return

    choice = Choice.objects.filter(id=choice_id).first()
    session = UserQuizSession.objects.filter(id=session_id).first()

    if not choice or not session:
        return

    UserQuizAnswer.objects.create(session=session, question=choice.question, choice=choice)

    next_question = choice.question.get_next()
    if next_question:
        SendMessages.Quizzes.question(user, next_question, session)
    else:
        session.finish()
        SendMessages.Quizzes.end(user, session)
