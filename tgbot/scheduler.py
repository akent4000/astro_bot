import time
import traceback
import signal
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loguru import logger
from django_redis import get_redis_connection

from tgbot import dispatcher
from tgbot.models import DailySubscription
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Constants

# Event для кооперативной остановки
sheduler_stop_event = threading.Event()

# Redis Lock ключ и таймаут (секунды)
SCHEDULER_LOCK_KEY = "tg_bot_scheduler_lock"
LOCK_TIMEOUT = 60

# Обработчик сигнала для корректной остановки
def sheduler_signal_handler(signum, frame):
    logger.info(f"Scheduler: получен сигнал {signum}, останавливаюсь...")
    sheduler_stop_event.set()

# Регистрируем обработчики SIGTERM и SIGINT
signal.signal(signal.SIGTERM, sheduler_signal_handler)
signal.signal(signal.SIGINT, sheduler_signal_handler)


def run_scheduler(stop_event: threading.Event):
    """
    Функция для фонового потока: берет Redis-блокировку,
    периодически продлевает её и каждую минуту отправляет факты.
    Прерывается по stop_event или при потере блокировки.
    """
    logger.info("Scheduler: пытаюсь получить лидирующий lock в Redis...")
    redis_conn = get_redis_connection("default")
    lock = redis_conn.lock(SCHEDULER_LOCK_KEY, timeout=LOCK_TIMEOUT, blocking=False)

    if not lock.acquire(blocking=False):
        logger.info("Scheduler: другой воркер держит lock, выходим")
        return

    logger.info("Scheduler: lock получен, начинаю работу")
    try:
        while not stop_event.is_set():
            try:
                now_utc = datetime.now(timezone.utc)
                moscow_tz = ZoneInfo(Constants.ZONE_INFO)
                now_moscow = now_utc.astimezone(moscow_tz)
                current_time = now_moscow.time().replace(second=0, microsecond=0)
                current_date = now_moscow.date()

                logger.debug(f"Scheduler: проверка подписок на {current_date} в {current_time}")
                subs = DailySubscription.objects.filter(send_time=current_time)
                for sub in subs.iterator():
                    SendMessages.IntFacts.today(sub.user, True)

                # Попытка продлить lock
                if not lock.extend(LOCK_TIMEOUT):
                    logger.warning("Scheduler: не удалось продлить lock, выходим")
                    break

                # Рассчитываем до следующей ровной минуты и проверяем stop_event каждую секунду
                next_minute = (now_moscow.replace(second=0, microsecond=0)
                               + timedelta(minutes=1))
                remaining = (next_minute - now_moscow).total_seconds()
                while remaining > 0 and not stop_event.is_set():
                    # ждем по одной секунде, проверяя stop_event
                    interval = 1 if remaining >= 1 else remaining
                    stop_event.wait(timeout=interval)
                    remaining -= interval

            except Exception as ex:
                logger.error(f"Scheduler: ошибка: {ex}\n{traceback.format_exc()}")
                # Короткая пауза перед повтором, проверяем stop_event каждую секунду
                remaining = 5
                while remaining > 0 and not stop_event.is_set():
                    interval = 1 if remaining >= 1 else remaining
                    stop_event.wait(timeout=interval)
                    remaining -= interval

    finally:
        try:
            lock.release()
            logger.info("Scheduler: lock освобожден")
        except Exception:
            logger.exception("Scheduler: ошибка при освобождении lock")
        logger.info("Scheduler: остановлен")

# Для внешнего завершения: достаточно удалить ключ lock в Redis:
#   redis-cli del tg_bot_scheduler_lock
