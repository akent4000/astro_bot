#!/usr/bin/env python3

import sys
import threading
import time
import traceback
from pathlib import Path

from django.core.management.base import BaseCommand
from tgbot import dispatcher
from tgbot.models import Configuration
from tgbot.logics.info_for_admins import send_messege_to_admins
from loguru import logger
from tgbot.scheduler import run_scheduler
from tgbot.logics.constants import Constants, Messages
from tgbot.bot_instances import instances
# Убедимся, что папка для логов существует
Path("logs").mkdir(parents=True, exist_ok=True)
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

_scheduler_thread = None

def _run_main_bot():
    """Устанавливает webhook для «главного» бота."""
    bot = dispatcher.get_main_bot()
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
    """Устанавливает webhook и регистрирует заглушки для тестового бота (только если test_mode=True)."""
    test_bot = dispatcher.get_test_bot()
    if test_bot is None:
        logger.warning("Тестовый бот не проинициализирован — пропускаем запуск.")
        return

    def _register_test_handlers():
        # Перехват всех обычных сообщений и reply-кнопок
        @test_bot.message_handler(func=lambda m: True)
        def handle_all_messages(message):
            from tgbot.user_helper import is_group_chat
            if is_group_chat(message):
                return
            test_bot.reply_to(
                message,
                text=Messages.IN_TEST_MODE_MESSAGE,
                parse_mode="Markdown"
            )

        # Перехват всех inline callback-кнопок
        @test_bot.callback_query_handler(func=lambda call: True)
        def handle_all_callback_queries(call):
            from tgbot.user_helper import is_group_chat
            if is_group_chat(call.message):
                return
            test_bot.answer_callback_query(
                callback_query_id=call.id,
                text=Messages.IN_TEST_MODE_MESSAGE,
                show_alert=False
            )
            test_bot.send_message(
                call.message.chat.id,
                Messages.IN_TEST_MODE_MESSAGE,
                parse_mode="Markdown"
            )

    # Если тестовый режим выключен — ничего не делаем
    if not Configuration.get_solo().test_mode:
        logger.info("Тестовый бот: test_mode=False — установка webhook не требуется.")
        return

    try:
        logger.info("Тестовый бот: регистрация обработчиков и установка webhook")
        _register_test_handlers()
        url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)
        test_bot.remove_webhook()
        test_bot.set_webhook(url=url)
        instances[Constants.TEST_BOT_WH_I] = test_bot
        logger.info("Тестовый бот: обработчики зарегистрированы, webhook установлен")
    except Exception:
        logger.exception("Ошибка при запуске тестового бота")



def start_bots():
    """Запускает два фоновых потока: один для основного бота, другой — для тестового."""
    logger.info("Запуск потоков ботов")
    _run_main_bot()
    _run_test_bot()
    _scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    _scheduler_thread.start()

class Command(BaseCommand):
    help = "Запускает два Telegram-бота (основной и тестовый) в режиме polling."

    def handle(self, *args, **options):
        start_bots()
        if _scheduler_thread:
            _scheduler_thread.join()
