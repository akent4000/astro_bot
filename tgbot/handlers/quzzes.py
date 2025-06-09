from telebot.types import CallbackQuery
from tgbot.dispatcher import get_main_bot
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import CallbackData, Messages
from tgbot.models import ArticlesSection, ArticlesSubsection, Choice, QuizTopic, QuizLevel, Quiz, UserQuizAnswer, UserQuizSession
from tgbot.logics.user_helper import get_user_from_call, extract_query_params, extract_int_param, get_callback_name_from_call
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например apod_api.py → logs/apod_api.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")
bot = get_main_bot()

# --- Обработчики QUIZZES ---
@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES)
def handle_quizzes(call: CallbackQuery):
    logger.info("Received QUIZZES callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for call: {}", call.data)
        return
    logger.debug("Sending topic list to user {}", user.id)
    SendMessages.Quizzes.choose_topic(user)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_TOPIC)
def handle_quizzes_topic(call: CallbackQuery):
    logger.info("Received QUIZZES_TOPIC callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params: {}", params)
    topic_id = extract_int_param(call, params, CallbackData.QUIZZES_TOPIC_ID, Messages.MISSING_PARAMETERS_ERROR)
    if topic_id is None:
        logger.error("Missing or invalid topic_id in params: {}", params)
        return

    topic = QuizTopic.objects.filter(id=topic_id).first()
    if not topic:
        logger.error("QuizTopic not found: id={} for user {}", topic_id, user.id)
        return

    logger.debug("Sending level choices for topic {} to user {}", topic.id, user.id)
    SendMessages.Quizzes.choose_level(user, topic)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_LEVEL)
def handle_quizzes_level(call: CallbackQuery):
    logger.info("Received QUIZZES_LEVEL callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params: {}", params)
    level_id = extract_int_param(call, params, CallbackData.QUIZZES_LEVEL_ID, Messages.MISSING_PARAMETERS_ERROR)
    topic_id = extract_int_param(call, params, CallbackData.QUIZZES_TOPIC_ID, Messages.MISSING_PARAMETERS_ERROR)
    if level_id is None or topic_id is None:
        logger.error("Missing or invalid level_id/topic_id in params: {}", params)
        return

    session_to_delete_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_SESSION_DELETE_ID,
    )
    if session_to_delete_id is not None:
        logger.debug("Deleting previous session id {} for user {}", session_to_delete_id, user.id)
        session_to_delete = UserQuizSession.objects.filter(id=session_to_delete_id).first()
        if session_to_delete:
            session_to_delete.delete()
            logger.info("Deleted session {}", session_to_delete_id)

    level = QuizLevel.objects.filter(id=level_id).first()
    topic = QuizTopic.objects.filter(id=topic_id).first()
    if not level or not topic:
        logger.error("Level or topic not found: level_id={}, topic_id={}", level_id, topic_id)
        return

    logger.debug("Sending quiz choices for topic {} level {} to user {}", topic.id, level.id, user.id)
    SendMessages.Quizzes.choose_quiz(user, topic, level)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_QUIZ)
def handle_quizzes_quiz(call: CallbackQuery):
    logger.info("Received QUIZZES_QUIZ callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params: {}", params)
    quiz_id = extract_int_param(call, params, CallbackData.QUIZZES_QUIZ_ID, Messages.MISSING_PARAMETERS_ERROR)
    if quiz_id is None:
        logger.error("Missing or invalid quiz_id in params: {}", params)
        return

    quiz = Quiz.objects.filter(id=quiz_id).first()
    if not quiz:
        logger.error("Quiz not found: id={}", quiz_id)
        return    

    question = quiz.questions.order_by("order").first()
    if not question:
        logger.error("No questions found for quiz id={}", quiz_id)
        return
    
    session = UserQuizSession.objects.create(user=user, quiz=quiz)
    logger.info("Created new session {} for user {} quiz {}", session.id, user.id, quiz.id)
    SendMessages.Quizzes.question(user, question, session)

@bot.callback_query_handler(func=lambda call: get_callback_name_from_call(call) == CallbackData.QUIZZES_QUIZ_QUESTION_CHOISE)
def handle_quizzes_question_choice(call: CallbackQuery):
    logger.info("Received QUIZZES_QUIZ_QUESTION_CHOISE callback: {}", call.data)
    user = get_user_from_call(call)
    if not user:
        logger.warning("User not found for call: {}", call.data)
        return

    params = extract_query_params(call)
    logger.debug("Extracted params: {}", params)

    choice_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_QUESTION_CHOISE_ID,
        Messages.MISSING_PARAMETERS_ERROR
    )
    session_id = extract_int_param(
        call,
        params,
        CallbackData.QUIZZES_QUIZ_SESSION_ID,
        Messages.MISSING_PARAMETERS_ERROR
    )
    if choice_id is None or session_id is None:
        logger.error("Missing or invalid choice_id/session_id in params: {}", params)
        return

    choice = Choice.objects.filter(id=choice_id).first()
    session = UserQuizSession.objects.filter(id=session_id).first()
    if not choice or not session:
        logger.error("Choice or session not found: choice_id={}, session_id={}", choice_id, session_id)
        return

    answer_obj, created = UserQuizAnswer.objects.get_or_create(session=session, question=choice.question, choice=choice)
    logger.debug("User {} selected choice {} (new={})", user.id, choice.id, created)

    next_question = choice.question.get_next()
    if next_question:
        logger.debug("Sending next question {} for session {}", next_question.id, session.id)
        SendMessages.Quizzes.question(user, next_question, session)
    else:
        session.finish()
        logger.info("Session {} finished for user {}", session.id, user.id)
        SendMessages.Quizzes.end(user, session)
