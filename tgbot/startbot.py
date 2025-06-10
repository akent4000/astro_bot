import os

import threading
from tgbot import dispatcher
from tgbot.bot_instances import instances
from tgbot.scheduler import run_scheduler, sheduler_stop_event
from tgbot.models import Configuration
from tgbot.logics.constants import Constants, Messages
from telebot.apihelper import ApiTelegramException
import time
from django.core.cache import cache
from pathlib import Path
from loguru import logger
# И создаём папку под логи
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")

MAIN_BOT_WH_SET = "main_wh_set"
TEST_BOT_WH_SET = "test_wh_set"
SHEDULER_SET = "sheduler_set"
CLEAR_CACHE = "clear_cache"

_sheduler_thread = None

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
    instances[Constants.MAIN_BOT_WH_I] = bot
    url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.MAIN_BOT_WH_I)
    if cache.add(MAIN_BOT_WH_SET, True, timeout=24*3600):
        # безопасный вызов с учётом 429
        max_retries = 3
        for attempt in range(1, max_retries+1):
            try:
                bot.remove_webhook()
                bot.set_webhook(url=url)
                logger.info(f"Webhook установлен в воркере PID {os.getpid()}")
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                    logger.warning(f"429 retry after {retry_after} sec (attempt {attempt})")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.exception(f"Ошибка set_webhook: {e}")
                    break
    else:
        logger.info("Webhook уже установлен другим воркером, PID %s пропускает", os.getpid())

def _run_test_bot():
    test_bot = dispatcher.get_test_bot()
    if not test_bot:
        logger.warning("Тестовый бот не проинициализирован — пропускаем.")
        return

    url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)

    # Кладём экземпляр в instances для каждого воркера
    instances[Constants.TEST_BOT_WH_I] = test_bot

    @test_bot.message_handler(func=lambda m: True)
    def _m(msg):
        from tgbot.user_helper import is_group_chat
        if is_group_chat(msg):
            return
        test_bot.reply_to(msg, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")

    @test_bot.callback_query_handler(func=lambda c: True)
    def _c(c):
        from tgbot.user_helper import is_group_chat
        if is_group_chat(c.message):
            return
        test_bot.answer_callback_query(c.id, text=Messages.IN_TEST_MODE_MESSAGE)
        test_bot.send_message(c.message.chat.id, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")

    # Только один воркер дальше будет регистрировать хэндлеры + ставить webhook
    if cache.add(TEST_BOT_WH_SET, True, timeout=24*3600):
        # 2) Установка webhook с учётом 429
        for attempt in range(1, 4):
            try:
                test_bot.remove_webhook()
                test_bot.set_webhook(url=url)
                logger.info(f"Test webhook установлен (PID {os.getpid()})")
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                    logger.warning(f"Test webhook rate limit, retry after {retry_after} sec (attempt {attempt})")
                    time.sleep(retry_after)
                    continue
                logger.exception(f"Ошибка установки webhook тестового бота: {e}")
                break
    else:
        logger.info(f"Test bot уже инициализирован другим воркером (PID {os.getpid()}), пропускаем регистрацию и webhook")

def reload_bots():
    _clear_cahce_once()
    logger.info(f"=== Начинаем полный перезапуск ботов (PID {os.getpid()}) ===")
    dispatcher._main_bot = None
    dispatcher._test_bot = None
    if _sheduler_thread:
        sheduler_stop_event.set()
        _sheduler_thread.join()
    _start_bots()
    _run_sheduler()
    logger.info("=== Перезапуск ботов завершён ===")

def _watch_config_changes(poll_interval: int = 5):
    """
    Фоновой тред: проверяет каждые poll_interval секунд,
    поменялся ли cache["tgbot_config_changed"] – и если да, вызывает reload_bots().
    """
    from django.core.cache import cache

    last = None
    while True:
        time.sleep(poll_interval)
        stamped = cache.get("tgbot_config_changed")
        if stamped and stamped != last:
            last = stamped
            try:
                reload_bots()
            except Exception:
                logger.exception("Ошибка при реактивном swap_bots() из watcher'а")

def _clear_cahce_once():
    if cache.add("redis_cache_flushed", True, timeout=10):
        logger.info(f"PID {os.getpid()}: сбрасываю Redis-кэш")
        cache.clear()
        logger.info(f"PID {os.getpid()}: Redis-кэш сброшен")
    else:
        logger.info(f"PID {os.getpid()}: кэш уже сбросил другой воркер")

def _run_sheduler():
    global _sheduler_thread
    if _sheduler_thread is None:
        if cache.add("tgbot_scheduler_started", True, timeout=24*3600):
            _sheduler_thread = threading.Thread(target=run_scheduler, args=(sheduler_stop_event,), name="DailyScheduler")
            logger.info(f"Scheduler запущен (PID {os.getpid()})")
        else:
            logger.info("Scheduler уже запущен другим воркером")
    else:
        logger.info(f"Scheduler уже инициализирован другим воркером (PID {os.getpid()}), пропускаем регистрацию и webhook")

def _start_bots():
    logger.info(f"Запуск ботов из ASGI-процесса (PID {os.getpid()})")
    _run_main_bot()
    _run_test_bot()
    

def start():
    _clear_cahce_once()
    _start_bots()
    _run_sheduler()
    threading.Thread(target=_watch_config_changes, daemon=True).start()
    logger.info(f"Запущен watcher конфигурации (PID {os.getpid()})")

