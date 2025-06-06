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

# Убедимся, что папка для логов существует
Path("logs").mkdir(parents=True, exist_ok=True)
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

_main_thread = None
_test_thread = None


def _run_main_bot():
    """Постоянный цикл polling для «главного» бота."""
    # При первом обращении берём экземпляр главного бота
    bot = dispatcher.get_main_bot()

    # Подключаем все обработчики
    from tgbot.handlers import commands, main_menu, moon_calc, apod, utils, int_facts, articles

    while True:
        try:
            logger.info("Основной бот: запуск polling")
            bot.polling(
                none_stop=True,
                interval=0,
                timeout=20,
                skip_pending=True
            )
        except Exception as e:
            logger.error(f"Ошибка в основном боте: {e}\n{traceback.format_exc()}")
            send_messege_to_admins(
                f"Ошибка в основном боте: {e}\n{traceback.format_exc()}\n\n"
                "Основной бот будет перезапущен."
            )
            try:
                bot.stop_polling()
            except Exception:
                pass
            time.sleep(1)
            logger.info("Перезапуск основного бота...")
        else:
            # Выходим из цикла, если polling завершился без ошибок
            break

    logger.info("Поток основного бота завершён")


def _run_test_bot():
    """Постоянный цикл polling для «тестового» бота (только если test_mode=True)."""
    test_bot = dispatcher.get_test_bot()
    if test_bot is None:
        logger.warning("Тестовый бот не проинициализирован, завершаем пуллинг тестового бота.")
        return

    # Подключить универсальный обработчик «все сообщения отвечаем, что технические работы»
    def _register_test_handlers():
        @test_bot.message_handler(func=lambda m: True)
        def handle_all_messages(message):
            from tgbot.user_helper import is_group_chat

            if is_group_chat(message):
                return
            test_bot.reply_to(
                message,
                "⚠️ *Технические работы*",
                parse_mode="Markdown"
            )

    while True:
        try:
            # Проверяем флаг test_mode в базе
            if Configuration.get_solo().test_mode:
                logger.info("Тестовый бот: запуск polling")
                _register_test_handlers()
                test_bot.polling(
                    none_stop=True,
                    interval=0,
                    timeout=20,
                    skip_pending=True
                )
            else:
                # Если test_mode отключён, просто ждём небольшую паузу
                time.sleep(1)
        except Exception as e:
            logger.error(f"Ошибка в тестовом боте: {e}\n{traceback.format_exc()}")
            try:
                test_bot.stop_polling()
            except Exception:
                pass
            time.sleep(1)
            logger.info("Перезапуск тестового бота...")
        else:
            # Если polling завершился без исключений — выходим
            break

    logger.info("Поток тестового бота завершён")


def start_bots():
    """Запускает два фоновых потока: один для основного бота, другой — для тестового."""
    global _main_thread, _test_thread

    logger.info("Запуск потоков ботов")
    _main_thread = threading.Thread(target=_run_main_bot, daemon=True)
    _test_thread = threading.Thread(target=_run_test_bot, daemon=True)
    _main_thread.start()
    _test_thread.start()


class Command(BaseCommand):
    help = "Запускает два Telegram-бота (основной и тестовый) в режиме polling."

    def handle(self, *args, **options):
        start_bots()

        # Блокируем основной процесс, пока потоки работают
        global _main_thread, _test_thread
        if _main_thread:
            _main_thread.join()
        if _test_thread:
            _test_thread.join()
