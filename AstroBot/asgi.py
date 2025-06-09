import os
from pathlib import Path
import threading
from django.core.cache import cache

# 1) Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AstroBot.settings')

# 2) Инициалищируем Django — сразу вызываем ASGI-приложение
from django.core.asgi import get_asgi_application
django_app  = get_asgi_application()

# 3) Теперь можно безопасно импортировать всё, что работает с ORM и AppConfig
from loguru import logger
from tgbot import dispatcher
from tgbot.bot_instances import instances
from tgbot.scheduler import run_scheduler
from tgbot.models import Configuration
from tgbot.logics.constants import Constants, Messages

# И создаём папку под логи
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")


def _run_main_bot():
    bot = dispatcher.get_main_bot()
    # Импорт хэндлеров только после того, как бот создан
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
    test_bot = dispatcher.get_test_bot()
    if not test_bot:
        logger.warning("Тестовый бот не проинициализирован — пропускаем.")
        return
    if not Configuration.get_solo().test_mode:
        logger.info("Test mode off — пропускаем тестовый бот.")
        return

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
    logger.info("Запуск ботов из ASGI-процесса")
    _run_main_bot()
    _run_test_bot()
    threading.Thread(target=run_scheduler, daemon=True).start()


# 4) Запускаем ботов уже в правильно инициализированном контексте
async def application(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                # Попытаемся установить флаг — только первый воркер увидит True
                if cache.add("tgbot_bots_started", True, timeout=24*3600):
                    # первый успешно "захватывает" запуск
                    threading.Thread(target=start_bots, daemon=True).start()
                    logger.info("start_bots() запущен первым воркером")
                else:
                    logger.info("start_bots() уже был запущен другим воркером — пропускаем")
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        await django_app(scope, receive, send)
