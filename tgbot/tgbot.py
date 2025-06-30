import os
import types
import sys
from pathlib import Path

# Workaround for Python 3.12 missing distutils
import sys, types

# Create stub distutils.version with minimal StrictVersion
_distutils_version = types.ModuleType('distutils.version')
class StrictVersion:
    """
    Minimal StrictVersion to compare version strings like '6.2.6'.
    """
    def __init__(self, v):
        parts = v.split('.')
        self.version = tuple(int(p) for p in parts if p.isdigit())
    def __lt__(self, other): return self.version < other.version
    def __le__(self, other): return self.version <= other.version
    def __eq__(self, other): return self.version == other.version
    def __ge__(self, other): return self.version >= other.version
    def __gt__(self, other): return self.version > other.version

# Register stub modules
sys.modules['distutils'] = types.ModuleType('distutils')
sys.modules['distutils.version'] = _distutils_version
setattr(_distutils_version, 'StrictVersion', StrictVersion)

import importlib
import threading
import asyncio
import time
from pathlib import Path
from loguru import logger
from telebot.apihelper import ApiTelegramException

from django.core.cache import cache
from django_redis import get_redis_connection

from tgbot import dispatcher
from tgbot.bot_instances import bots
from tgbot.scheduler import run_scheduler, sheduler_stop_event
from tgbot.logics.constants import Constants, Messages

from aioredlock import Aioredlock, LockError

# Создаём папку под логи
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")

# Настройка Redlock менеджера
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
dlmanager = Aioredlock([
    {"host": REDIS_HOST, "port": REDIS_PORT}
])

# Ключи блокировок
MAIN_BOT_LOCK = Constants.MAIN_BOT_LOCK
TEST_BOT_LOCK = Constants.TEST_BOT_LOCK
SCHEDULER_LOCK = Constants.SCHEDULER_LOCK
CONFIG_CHANGED = Constants.CONFIG_CHANGED

_scheduler_thread = None
_scheduler_lock = None

async def _setup_webhook(bot, lock_key, url, description):
    """
    Универсальная функция для захвата блокировки, установки вебхука и снятия блокировки.
    """
    try:
        lock = await dlmanager.lock(lock_key)
    except LockError:
        logger.info(f"(PID {os.getpid()} — пропускает) Webhook {description} уже установлен другим воркером")
        return

    try:
        for attempt in range(1, Constants.MAX_RETRIES_TO_SET_WEBHOOK + 1):
            try:
                bot.remove_webhook()
                bot.set_webhook(url=url)
                logger.info(f"(PID {os.getpid()}) Webhook {description} установлен")
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                    logger.warning(f"429 retry after {retry_after} sec (attempt {attempt})")
                    await asyncio.sleep(retry_after)
                else:
                    logger.exception(f"(PID {os.getpid()}) Ошибка set_webhook {description}: {e}")
                    break
    finally:
        try:
            await dlmanager.unlock(lock)
            logger.debug(f"(PID {os.getpid()}) Lock {description} освобождён")
        except Exception:
            logger.exception(f"(PID {os.getpid()}) Не удалось освободить lock для {description}")

async def _run_main_bot():
    bot = dispatcher.get_main_bot()
    # Импорт хэндлеров после создания бота
    for module_name in (
        'tgbot.handlers.commands',
        'tgbot.handlers.main_menu',
        'tgbot.handlers.moon_calc',
        'tgbot.handlers.apod',
        'tgbot.handlers.int_facts',
        'tgbot.handlers.articles',
        'tgbot.handlers.quzzes',
    ):
        importlib.reload(importlib.import_module(module_name))

    bots[Constants.MAIN_BOT_WH_I] = bot
    url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.MAIN_BOT_WH_I)
    await _setup_webhook(bot, MAIN_BOT_LOCK, url, "основного бота")

async def _run_test_bot():
    test_bot = dispatcher.get_test_bot()
    if not test_bot:
        logger.warning("Тестовый бот не проинициализирован — пропускаем.")
        return

    # Регистрация общих handlers
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

    bots[Constants.TEST_BOT_WH_I] = test_bot
    url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)
    await _setup_webhook(test_bot, TEST_BOT_LOCK, url, "тестового бота")

async def _acquire_scheduler_lock():
    global _scheduler_lock
    try:
        _scheduler_lock = await dlmanager.lock(SCHEDULER_LOCK)
        return True
    except LockError:
        return False

def _start_bots():
    """
    Запускает задачи по установке вебхуков для основных и тестовых ботов
    в отдельных потоках с собственными event loop.
    """
    logger.info(f"Запуск ботов из ASGI (PID {os.getpid()})")
    # Запуск асинхронных задач в отдельных потоках
    threading.Thread(
        target=lambda: asyncio.run(_run_main_bot()),
        daemon=True,
        name="MainBotThread"
    ).start()
    threading.Thread(
        target=lambda: asyncio.run(_run_test_bot()),
        daemon=True,
        name="TestBotThread"
    ).start()

# Запуск шедулера с блокировкой через aioredlock
def _run_sheduler():
    global _scheduler_thread, _scheduler_lock
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    sheduler_stop_event.clear()

    # Создаём и используем собственный event loop для асинхронного захвата lock
    loop = asyncio.new_event_loop()
    try:
        got_lock = loop.run_until_complete(_acquire_scheduler_lock())
    finally:
        loop.close()

    if not got_lock:
        logger.info(f"Scheduler уже запущен другим воркером (PID {os.getpid()}) — пропускаем")
        return

    # Запускаем фоновый поток выполнения задач
    _scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(sheduler_stop_event,),
        daemon=True,
        name="DailySchedulerThread"
    )
    _scheduler_thread.start()
    logger.info(f"Scheduler запущен (PID {os.getpid()})")

# Watcher для реактивного перезапуска
def _watch_config_changes(poll_interval: int = 5):
    last = None
    while True:
        time.sleep(poll_interval)
        stamped = cache.get(CONFIG_CHANGED)
        if stamped and stamped != last:
            last = stamped
            try:
                reload_bots()
            except Exception:
                logger.exception("Ошибка при reload_bots() из watcher'а")

# Перезапуск ботов и шедулера
def reload_bots():
    global _scheduler_thread, _scheduler_lock
    # Останавливаем старый шедулер
    if _scheduler_thread and _scheduler_thread.is_alive():
        sheduler_stop_event.set()
        _scheduler_thread.join()
        if _scheduler_lock:
            asyncio.get_event_loop().run_until_complete(dlmanager.unlock(_scheduler_lock))
        _scheduler_thread = None
        _scheduler_lock = None

    dispatcher._main_bot = None
    dispatcher._test_bot = None
    _clear_cache_once()
    _start_bots()
    _run_sheduler()
    logger.info("=== Перезапуск ботов и Scheduler завершён ===")

# Инициализация при старте приложения

def _clear_cache_once():
    """Очищает ключи блокировок в Redis единожды при старте или перезапуске приложения"""
    CLEAR_FLAG = Constants.CLEAR_FLAG
    try:
        # cache.add вернёт True только один раз за timeout
        if cache.add(CLEAR_FLAG, True, timeout=20):
            logger.info(f"PID {os.getpid()}: сбрасываю кэш блокировок Redis")
            cache.delete_many([Constants.MAIN_BOT_LOCK, Constants.TEST_BOT_LOCK, Constants.SCHEDULER_LOCK])
            logger.info(f"PID {os.getpid()}: кэш блокировок сброшен")
    except Exception:
        logger.exception("Ошибка при очистке кэша блокировок")

def start():
    _clear_cache_once()
    _start_bots()
    _run_sheduler()
    threading.Thread(target=_watch_config_changes, daemon=True).start()
    logger.info(f"Watcher конфигурации запущен (PID {os.getpid()})")
