# tgbot/scheduler.py

import time
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytz
from loguru import logger

from tgbot import dispatcher
from tgbot.models import DailySubscription, InterestingFact
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Constants, Messages

#
def run_scheduler():
    """
    Фоновая функция, которую запускают в отдельном потоке.
    Каждую «ровную» минуту проверяет, у кого send_time совпадает с текущим московским временем,
    а потом пытается отправить этим пользователям факт на сегодня (если он есть).
    """
    logger.info("Scheduler: запущен")

    while True:
        try:
            # Получаем текущий UTC-время с tzinfo
            now_utc = datetime.now(timezone.utc)

            # Переводим в московский часовой пояс, взятый из Constants.ZONE_INFO
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
            time.sleep(sleep_seconds)

        except Exception as ex:
            logger.error(f"Scheduler: упало с ошибкой: {ex}\n{traceback.format_exc()}")
            # Если что-то пошло не так, ждём 30 секунд и повторяем
            time.sleep(30)
