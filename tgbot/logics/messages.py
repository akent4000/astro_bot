# tgbot/logics/messages.py

import time
import re
from typing import Optional, Iterable, Union

from tgbot.dispatcher import bot

from tgbot.logics.apod_api import APODClient, APODClientError
from tgbot.logics.keyboards import *
from tgbot.logics.text_helper import escape_markdown, get_mention, safe_markdown_mention
from tgbot.models import *
from tgbot.logics.constants import *
from telebot.types import InputMediaPhoto, InputMediaVideo, MessageEntity, CallbackQuery, InlineKeyboardMarkup
from tgbot.logics.keyboards import Keyboards
from pathlib import Path
from loguru import logger
import datetime
from zoneinfo import ZoneInfo

from tgbot.logics.moon_calc import moon_phase
# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например messages.py → logs/messages.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")

from telebot.apihelper import ApiException
from tgbot.dispatcher import bot
from tgbot.models import SentMessage, TelegramUser


class SendMessages:
    @staticmethod
    def _update_or_replace_last(user: TelegramUser,
                                forced_delete: bool,
                                send_func,
                                edit_func):
        """
        Вспомогательный метод: пытается отредактировать последнее сообщение,
        если не получается — удаляет его и отправляет новое.

        send_func: функция без аргументов, возвращает объект Message при отправке
        edit_func: функция(chat_id, message_id) — возвращает объект Message при редактировании
        """
        chat_id = user.chat_id
        logger.debug(f"_update_or_replace_last: user={user}, forced_delete={forced_delete}")

        # 1) Принудительное удаление всех старых сообщений
        if forced_delete:
            logger.info(f"_update_or_replace_last: forced_delete=True, удаляем все старые сообщения для user={user}.")
            try:
                qs = SentMessage.objects.filter(telegram_user=user)
                ids = list(qs.values_list("message_id", flat=True))
                if ids:
                    logger.debug(f"_update_or_replace_last: пытаемся bot.delete_messages ids={ids}")
                    bot.delete_messages(chat_id, ids)
                qs.delete()
                logger.info(f"_update_or_replace_last: удалены все записи SentMessage для user={user}.")
            except Exception as e:
                logger.error(f"_update_or_replace_last: ошибка при forced_delete: {e}")
                SentMessage.objects.filter(telegram_user=user).delete()

        # 2) Последнее отправленное сообщение
        last = SentMessage.objects.filter(telegram_user=user).order_by("-created_at").first()
        if last:
            logger.debug(f"_update_or_replace_last: найдено последнее сообщение message_id={last.message_id} для user={user}.")
        else:
            logger.debug(f"_update_or_replace_last: нет предыдущих сообщений для user={user}.")

        # 3) Если нет — просто отправляем новое и сохраняем
        if not last:
            try:
                new_msg = send_func()
                SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)
                logger.info(f"_update_or_replace_last: отправлено новое сообщение message_id={new_msg.message_id} для user={user}.")
                return new_msg
            except Exception as e:
                logger.error(f"_update_or_replace_last: ошибка при send_func: {e}")
                raise

        msg_id = last.message_id

        # 4) Пытаемся отредактировать
        try:
            logger.debug(f"_update_or_replace_last: пробуем редактировать message_id={msg_id} для user={user}.")
            edited = edit_func(chat_id, msg_id)
            logger.info(f"_update_or_replace_last: успешно отредактировано сообщение message_id={msg_id} для user={user}.")
            return edited
        except ApiException as e:
            logger.warning(f"_update_or_replace_last: не удалось отредактировать message_id={msg_id}, ошибка: {e}")
            # 5) Если редактирование не удалось — удаляем старое и отправляем новое
            try:
                logger.debug(f"_update_or_replace_last: пытаемся bot.delete_message message_id={msg_id}.")
                bot.delete_message(chat_id=chat_id, message_id=msg_id)
                logger.info(f"_update_or_replace_last: удалено старое сообщение message_id={msg_id}.")
            except ApiException as ex:
                logger.warning(f"_update_or_replace_last: ошибка при удалении старого message_id={msg_id}: {ex}")

            try:
                new_msg = send_func()
                SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)
                logger.info(f"_update_or_replace_last: отправлено новое сообщение message_id={new_msg.message_id} для user={user}.")
                return new_msg
            except Exception as ex2:
                logger.error(f"_update_or_replace_last: ошибка при отправке нового сообщения: {ex2}")
                raise

    @staticmethod
    def update_or_replace_last_message(user: TelegramUser,
                                       forced_delete: bool,
                                       text: str,
                                       **kwargs):
        """
        Обновляет или заменяет последнее текстовое сообщение.

        Параметры:
            user: TelegramUser
            forced_delete: если True — удаляем всё перед попыткой редактирования
            text: текст для send_message / edit_message_text
            **kwargs: 'reply_markup', 'parse_mode' и т.д.
        """
        logger.debug(f"update_or_replace_last_message: user={user}, forced_delete={forced_delete}, text={text}")
        send_fn = lambda: bot.send_message(chat_id=user.chat_id, text=text, **kwargs)
        edit_fn = lambda chat_id, message_id: bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, **kwargs
        )
        return SendMessages._update_or_replace_last(user, forced_delete, send_fn, edit_fn)

    @staticmethod
    def update_or_replace_last_photo(user: TelegramUser,
                                     forced_delete: bool,
                                     photo,
                                     caption: str = "",
                                     **kwargs):
        """
        Обновляет или заменяет последнее сообщение с фото.

        Параметры:
            user: TelegramUser
            forced_delete: если True — удаляем всё перед попыткой редактирования
            photo: file_id (str) или объект BytesIO/файла или URL
            caption: подпись для фото
            **kwargs: 'reply_markup', 'parse_mode' и т.д.
        """
        logger.debug(f"update_or_replace_last_photo: user={user}, forced_delete={forced_delete}, caption={caption}")
        send_fn = lambda: bot.send_photo(
            chat_id=user.chat_id, photo=photo, caption=caption, **kwargs
        )

        def edit_fn(chat_id, message_id):
            logger.debug(f"update_or_replace_last_photo.edit_fn: пытаемся редактировать media для message_id={message_id}")
            media = InputMediaPhoto(media=photo, caption=caption)
            sent = bot.edit_message_media(
                chat_id=chat_id, message_id=message_id, media=media
            )
            caption_kwargs = {k: v for k, v in kwargs.items() if k in ("reply_markup", "parse_mode")}
            if caption_kwargs:
                logger.debug(f"update_or_replace_last_photo.edit_fn: обновляем подпись/клавиатуру для message_id={message_id}")
                bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    **caption_kwargs
                )
            return sent

        return SendMessages._update_or_replace_last(user, forced_delete, send_fn, edit_fn)

    class MainMenu:
        @staticmethod
        def menu(user: TelegramUser, forced_delete: bool = False):
            logger.debug(f"MainMenu.menu: user={user}, forced_delete={forced_delete}")
            SendMessages.update_or_replace_last_message(
                user,
                forced_delete,
                text=Messages.MENU_MESSAGE,
                reply_markup=Keyboards.MainMenu.menu(),
                parse_mode="Markdown"
            )

    class MoonCalc:
        @staticmethod
        def menu(user: TelegramUser):
            logger.debug(f"MoonCalc.menu: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.MOON_CALC,
                reply_markup=Keyboards.MoonCalc.menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def today(user: TelegramUser):
            moscow_tz = ZoneInfo('Europe/Moscow')
            today_moscow = datetime.datetime.now(moscow_tz).date()
            formatted_date = today_moscow.strftime("%d.%m.%Y")
            phase = moon_phase(today_moscow)
            text = Messages.MOON_CALC_TODAY.format(date=formatted_date, moon_phase=phase)
            logger.debug(f"MoonCalc.today: user={user}, date={formatted_date}, phase={phase}")

            return SendMessages.update_or_replace_last_message(
                user,
                False,
                text=text,
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def enter_date(user: TelegramUser):
            logger.debug(f"MoonCalc.enter_date: user={user}")
            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=Messages.MOON_CALC_ENTER_DATE,
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def incorrect_enter_date(user: TelegramUser):
            logger.debug(f"MoonCalc.incorrect_enter_date: user={user}")
            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=Messages.MOON_CALC_ENTER_DATE_INCORRECT,
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def date(user: TelegramUser, date: datetime.datetime):
            formatted_date = date.date().strftime("%d.%m.%Y")
            phase = moon_phase(date)
            text = Messages.MOON_CALC_MSG.format(date=formatted_date, moon_phase=phase)
            logger.debug(f"MoonCalc.date: user={user}, date={formatted_date}, phase={phase}")

            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=text,
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(),
                parse_mode="Markdown"
            )

    class Apod:
        @staticmethod
        def send_apod(user: TelegramUser):
            """
            Отправляет (или обновляет) сообщение с APOD сегодняшнего дня.
            Если telegram_media_id уже есть, обновляет существующее фото через
            SendMessages.update_or_replace_last_photo. Иначе скачивает картинку
            и сохраняет новый telegram_media_id.
            """
            chat_id = user.chat_id
            logger.debug(f"Apod.send_apod: user={user}")

            # Получаем API-ключ из модели-одиночки ApodApiKey
            api_key = ApodApiKey.get_solo().api_key
            if not api_key:
                logger.error("Apod.send_apod: отсутствует API-ключ ApodApiKey")
                bot.send_message(chat_id, "API-ключ APOD не задан.")
                return

            try:
                client = APODClient(api_key=api_key)
                logger.info("Apod.send_apod: APODClient успешно инициализирован")
            except APODClientError as e:
                logger.error(f"Apod.send_apod: ошибка инициализации APODClient: {e}")
                bot.send_message(chat_id, f"Не удалось инициализировать APOD-клиент: {e}")
                return

            try:
                # 1) Получаем или обновляем запись ApodFile для сегодняшней даты
                apod_obj = client.get_or_update_today()
                logger.info(f"Apod.send_apod: получен ApodFile для даты {apod_obj.date}")

                # 2) Если media_id уже есть, просто обновляем существующее сообщение с фото
                if apod_obj.telegram_media_id:
                    logger.debug(f"Apod.send_apod: media_id={apod_obj.telegram_media_id} уже есть, обновляем фото")
                    SendMessages.update_or_replace_last_photo(
                        user=user,
                        forced_delete=True,
                        photo=apod_obj.telegram_media_id,
                        caption=apod_obj.title or "",
                        reply_markup=Keyboards.Apod.back_to_menu(),
                    )
                    return

                # 3) Иначе скачиваем изображение в память
                date_str = apod_obj.date.strftime("%Y-%m-%d")
                logger.info(f"Apod.send_apod: скачиваем изображение для даты {date_str}")
                image_buffer = client.fetch_image_bytes(date_str)
                image_buffer.seek(0)

                # 4) Отправляем фото, используя helper, и сохраняем новый file_id
                logger.debug("Apod.send_apod: отправка нового фото")
                def send_new():
                    return bot.send_photo(chat_id, image_buffer, caption=apod_obj.title or "", reply_markup=Keyboards.Apod.back_to_menu())

                def edit_existing(chat_id, message_id):
                    media = InputMediaPhoto(media=image_buffer, caption=apod_obj.title or "")
                    logger.debug(f"Apod.send_apod.edit_existing: редактируем сообщение message_id={message_id}")
                    sent = bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
                    return sent

                result_msg = SendMessages._update_or_replace_last(
                    user=user,
                    forced_delete=True,
                    send_func=send_new,
                    edit_func=edit_existing,
                )
                if hasattr(result_msg, 'photo'):
                    file_id = result_msg.photo[-1].file_id
                    apod_obj.telegram_media_id = file_id
                    apod_obj.save(update_fields=["telegram_media_id"])
                    logger.info(f"Apod.send_apod: сохранён новый telegram_media_id={file_id} для даты {apod_obj.date}")

            except APODClientError as e:
                logger.error(f"Apod.send_apod: ошибка при получении APOD: {e}")
                bot.send_message(chat_id, f"Ошибка при получении APOD: {e}")
            except Exception as e:
                logger.exception("Apod.send_apod: внутренняя ошибка при отправке APOD")
                bot.send_message(chat_id, "Произошла внутренняя ошибка при отправке APOD.")
