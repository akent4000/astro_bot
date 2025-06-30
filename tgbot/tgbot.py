import os
import types
import sys
import importlib
import threading
import asyncio
import time
from pathlib import Path
from loguru import logger
from telebot.apihelper import ApiTelegramException

from django.core.cache import cache

from tgbot import dispatcher
from tgbot.bot_instances import bots
from tgbot.scheduler import run_scheduler, sheduler_stop_event
from tgbot.logics.constants import Constants, Messages

from aioredlock import Aioredlock, LockError

# Workaround for Python 3.12 missing distutils
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

sys.modules['distutils'] = types.ModuleType('distutils')
sys.modules['distutils.version'] = _distutils_version
setattr(_distutils_version, 'StrictVersion', StrictVersion)

# Setup logging directory
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")

# Redlock manager
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
dlmanager = Aioredlock([
    {"host": REDIS_HOST, "port": REDIS_PORT}
])

# Lock keys
MAIN_BOT_LOCK = Constants.MAIN_BOT_LOCK
TEST_BOT_LOCK = Constants.TEST_BOT_LOCK
SCHEDULER_LOCK = Constants.SCHEDULER_LOCK
CONFIG_CHANGED = Constants.CONFIG_CHANGED

_scheduler_thread = None
_scheduler_lock = None

async def _setup_webhook(bot, lock_key, url, description):
    """
    Acquire lock, set webhook, release lock.
    """
    try:
        lock = await dlmanager.lock(lock_key)
    except LockError:
        logger.info(f"(PID {os.getpid()}) Webhook {description} already set by another worker")
        return
    try:
        for attempt in range(1, Constants.MAX_RETRIES_TO_SET_WEBHOOK + 1):
            try:
                bot.remove_webhook()
                bot.set_webhook(url=url)
                logger.info(f"(PID {os.getpid()}) Webhook {description} set")
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                    logger.warning(f"429 rate limit, retry after {retry_after}s (attempt {attempt})")
                    await asyncio.sleep(retry_after)
                else:
                    logger.exception(f"(PID {os.getpid()}) Error setting webhook {description}: {e}")
                    break
    finally:
        try:
            await dlmanager.unlock(lock)
            logger.debug(f"(PID {os.getpid()}) Lock released for {description}")
        except Exception:
            logger.exception(f"(PID {os.getpid()}) Failed to release lock for {description}")


def _main_bot_worker():
    """
    Synchronous wrapper to get main bot and setup webhook.
    """
    bot = dispatcher.get_main_bot()
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
    asyncio.run(_setup_webhook(bot, MAIN_BOT_LOCK, url, "main bot"))


def _test_bot_worker():
    """
    Synchronous wrapper to get test bot and setup webhook.
    """
    test_bot = dispatcher.get_test_bot()
    if not test_bot:
        logger.warning("Test bot not initialized — skipping.")
        return
    @test_bot.message_handler(func=lambda m: True)
    def _m(msg):
        from tgbot.user_helper import is_group_chat
        if is_group_chat(msg): return
        test_bot.reply_to(msg, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")
    @test_bot.callback_query_handler(func=lambda c: True)
    def _c(c):
        from tgbot.user_helper import is_group_chat
        if is_group_chat(c.message): return
        test_bot.answer_callback_query(c.id, text=Messages.IN_TEST_MODE_MESSAGE)
        test_bot.send_message(c.message.chat.id, Messages.IN_TEST_MODE_MESSAGE, parse_mode="Markdown")
    bots[Constants.TEST_BOT_WH_I] = test_bot
    url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)
    asyncio.run(_setup_webhook(test_bot, TEST_BOT_LOCK, url, "test bot"))

async def _acquire_scheduler_lock():
    global _scheduler_lock
    try:
        _scheduler_lock = await dlmanager.lock(SCHEDULER_LOCK)
        return True
    except LockError:
        return False


def _start_bots():
    logger.info(f"Starting bots (PID {os.getpid()})")
    threading.Thread(target=_main_bot_worker, daemon=True, name="MainBotThread").start()
    threading.Thread(target=_test_bot_worker, daemon=True, name="TestBotThread").start()


def _run_sheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    sheduler_stop_event.clear()
    loop = asyncio.new_event_loop()
    try:
        got = loop.run_until_complete(_acquire_scheduler_lock())
    finally:
        loop.close()
    if not got:
        logger.info(f"Scheduler already running elsewhere (PID {os.getpid()}) — skipping")
        return
    _scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(sheduler_stop_event,),
        daemon=True,
        name="DailySchedulerThread"
    )
    _scheduler_thread.start()
    logger.info(f"Scheduler started (PID {os.getpid()})")


def _watch_config_changes(interval=5):
    last = None
    while True:
        time.sleep(interval)
        stamped = cache.get(CONFIG_CHANGED)
        if stamped and stamped != last:
            last = stamped
            try:
                reload_bots()
            except Exception:
                logger.exception("Error on reload_bots from watcher")


def reload_bots():
    global _scheduler_thread
    sheduler_stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join()
    if _scheduler_lock:
        asyncio.run(dlmanager.unlock(_scheduler_lock))
    dispatcher._main_bot = None
    dispatcher._test_bot = None
    _clear_cache_once()
    _start_bots()
    _run_sheduler()
    logger.info("Reload complete")


def _clear_cache_once():
    flag = Constants.CLEAR_FLAG
    if cache.add(flag, True, timeout=20):
        logger.info(f"PID {os.getpid()}: Clearing Redis lock cache")
        cache.delete_many([MAIN_BOT_LOCK, TEST_BOT_LOCK, SCHEDULER_LOCK])


def start():
    _clear_cache_once()
    _start_bots()
    _run_sheduler()
    threading.Thread(target=_watch_config_changes, daemon=True).start()
    logger.info(f"Config watcher started (PID {os.getpid()})")
