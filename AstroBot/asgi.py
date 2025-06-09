import os
from pathlib import Path
import threading

# 1) Задаём переменную окружения до любых обращений к Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AstroBot.settings')

# 2) Импортируем и инициализируем Django
from django.core.asgi import get_asgi_application
application = get_asgi_application()

# 3) Теперь безопасно работать с ORM
from loguru import logger
from tgbot import dispatcher
from tgbot.bot_instances import instances
from tgbot.scheduler import run_scheduler
from tgbot.models import Configuration
from tgbot.logics.constants import Constants, Messages

# Убедимся, что папка для логов существует
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")


def _run_main_bot():
    """Инициализируем и вешаем webhook на главный бот."""
    bot = dispatcher.get_main_bot()
    # Импортируем модули с декораторами (они уже регистрируют хэндлеры на dispatcher)
    import tgbot.handlers.commands
    import tgbot.handlers.main_menu
    import tgbot.handlers.moon_calc
    import tgbot.handlers.apod
    import tgbot.handlers.int_facts
    import tgbot.handlers.articles
    import tgbot.handlers.quzzes

    try:
        logger.info("Основной бот: установка webhook")
        url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.MAIN_BOT_WH_I)
        bot.remove_webhook()
        bot.set_webhook(url=url)
        instances[Constants.MAIN_BOT_WH_I] = bot
        logger.info("Основной бот: webhook успешно установлен")
    except Exception:
        logger.exception("Ошибка при установке webhook у основного бота")


def _run_test_bot():
    """Инициализируем и вешаем webhook на тестовый бот (если test_mode=True)."""
    test_bot = dispatcher.get_test_bot()
    if not test_bot:
        logger.warning("Тестовый бот не проинициализирован — пропускаем.")
        return

    if not Configuration.get_solo().test_mode:
        logger.info("Test mode off — пропускаем тестовый бот.")
        return

    # Регистрируем «заглушки» для тестового бота
    def _register_test_handlers():
        @test_bot.message_handler(func=lambda m: True)
        def _m(_msg):
            from tgbot.user_helper import is_group_chat
            if is_group_chat(_msg):
                return
            test_bot.reply_to(_msg, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")

        @test_bot.callback_query_handler(func=lambda c: True)
        def _c(c):
            from tgbot.user_helper import is_group_chat
            if is_group_chat(c.message):
                return
            test_bot.answer_callback_query(c.id, text=Messages.IN_TEST_MODE_MESSAGE)
            test_bot.send_message(c.message.chat.id, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")

    try:
        logger.info("Тестовый бот: регистрация заглушек и установка webhook")
        _register_test_handlers()
        url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)
        test_bot.remove_webhook()
        test_bot.set_webhook(url=url)
        instances[Constants.TEST_BOT_WH_I] = test_bot
        logger.info("Тестовый бот: webhook установлен")
    except Exception:
        logger.exception("Ошибка при установке webhook у тестового бота")


def start_bots():
    """Запускаем webhooks и планировщик в фоновых потоках одного процесса."""
    logger.info("Запуск ботов из ASGI-процесса")
    _run_main_bot()
    _run_test_bot()

    sched_thread = threading.Thread(target=run_scheduler, daemon=True)
    sched_thread.start()
    # Чтобы main thread не завершился, можно дождаться scheduler или ждать бесконечно:
    # sched_thread.join()
    # или
    # threading.Event().wait()

# 4) Запускаем ботов при импорте asgi.py, но уже в полностью инициализированном Django
start_bots()
