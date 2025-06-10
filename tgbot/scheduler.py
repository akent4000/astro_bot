import time
import traceback
import signal
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytz
from loguru import logger

from tgbot import dispatcher
from tgbot.models import DailySubscription, InterestingFact
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Constants, Messages

# Event для кооперативной остановки
sheduler_stop_event = threading.Event()

# Обработчик сигнала для корректной остановки
def sheduler_signal_handler(signum, frame):
    logger.info(f"Scheduler: получен сигнал {signum}, останавливаюсь...")
    sheduler_stop_event.set()

# Регистрируем обработчики SIGTERM и SIGINT
signal.signal(signal.SIGTERM, sheduler_signal_handler)
signal.signal(signal.SIGINT, sheduler_signal_handler)

def run_scheduler(stop_event: threading.Event):
    """
    Фоновая функция, которую запускают в отдельном потоке.
    Каждую «ровную» минуту проверяет, у кого send_time совпадает с текущим временем,
    а потом пытается отправить этим пользователям факт на сегодня (если он есть).
    Можно корректно остановить через stop_event.set().
    """
    logger.info("Scheduler: запущен")

    # Работаем, пока stop_event не установлен
    while not stop_event.is_set():
        try:
            # Получаем текущий UTC-время с tzinfo
            now_utc = datetime.now(timezone.utc)

            # Переводим в московский часовой пояс
            moscow_tz = ZoneInfo(Constants.ZONE_INFO)
            now_moscow = now_utc.astimezone(moscow_tz)

            # Обрезаем секунды и миллисекунды
            current_time = now_moscow.time().replace(second=0, microsecond=0)
            current_date = now_moscow.date()

            logger.debug(f"Scheduler: проверяем подписки на {current_date} в {current_time}")

            # Найти всех подписчиков, чьё send_time == current_time
            subs = DailySubscription.objects.filter(send_time=current_time)
            if subs.exists():
                for sub in subs:
                    user = sub.user
                    SendMessages.IntFacts.today(user, True)

            # Высчитываем, сколько секунд ждать до следующей «ровной» минуты
            next_minute = (now_moscow.replace(second=0, microsecond=0) + timedelta(minutes=1))
            sleep_seconds = (next_minute - now_moscow).total_seconds()

            # Ждём, но прерываем сон, если установлен stop_event
            stop_event.wait(timeout=sleep_seconds)

        except Exception as ex:
            logger.error(f"Scheduler: упало с ошибкой: {ex}\n{traceback.format_exc()}")
            # Если что-то пошло не так, ждём 30 секунд и повторяем
            stop_event.wait(timeout=5)

    logger.info("Scheduler: остановлен")