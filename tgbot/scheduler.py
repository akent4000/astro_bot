# tgbot/scheduler.py

import time
import traceback
from datetime import datetime, timedelta

import pytz
from loguru import logger

from tgbot import dispatcher
from tgbot.models import DailySubscription, InterestingFact
from tgbot.logics.messages import SendMessages
from tgbot.logics.constants import Messages

# Таймзона для рассылок — Москва
MOSCOW_TZ = pytz.timezone("Europe/Moscow")


def run_scheduler():
    """
    Фоновая функция, которую запускают в отдельном потоке.
    Каждую «ровную» минуту проверяет, у кого send_time совпадает с текущим московским временем,
    а потом пытается отправить этим пользователям факт на сегодня (если он есть).
    """
    logger.info("Scheduler: запущен")

    while True:
        try:
            # Рассчитываем текущее московское время (UTC → UTC+3)
            now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
            now_moscow = now_utc.astimezone(MOSCOW_TZ)

            # Обрезаем секунды и миллисекунды
            current_time = now_moscow.time().replace(second=0, microsecond=0)
            current_date = now_moscow.date()

            logger.debug(f"Scheduler: проверяем подписки на {current_date} в {current_time}")

            # Найти всех подписчиков, чьё send_time == current_time
            subs = DailySubscription.objects.filter(send_time=current_time)
            if subs.exists():
                # Берём первый доступный факт на сегодня (если есть)
                fact = InterestingFact.objects.filter(date_to_mailing=current_date).first()

                for sub in subs:
                    user = sub.user
                    if fact:
                        # Отправляем пользователю факт через готовый метод
                        try:
                            SendMessages.IntFacts.today(user)
                            logger.info(f"Scheduler: отправлен факт (id={fact.id}) пользователю {user}")
                        except Exception as e2:
                            logger.error(f"Scheduler: не удалось отправить факт пользователю {user}: {e2}")
                    else:
                        # Если факта на сегодня нет, присылаем уведомление об этом
                        try:
                            dispatcher.get_main_bot().send_message(
                                chat_id=user.chat_id,
                                text=Messages.INT_FACTS_FACT_TODAY_NOT_FOUND
                            )
                            logger.info(f"Scheduler: уведомление об отсутствии факта отправлено {user}")
                        except Exception as e3:
                            logger.error(f"Scheduler: не удалось отправить уведомление об отсутствии факта {user}: {e3}")

            # Высчитываем, сколько секунд ждать до следующей «ровной» минуты
            next_minute = (now_moscow.replace(second=0, microsecond=0) + timedelta(minutes=1))
            sleep_seconds = (next_minute - now_moscow).total_seconds()
            time.sleep(sleep_seconds)

        except Exception as ex:
            logger.error(f"Scheduler: упало с ошибкой: {ex}\n{traceback.format_exc()}")
            # Если что-то пошло не так, ждём 30 секунд и повторяем
            time.sleep(30)
