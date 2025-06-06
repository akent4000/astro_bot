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

# Лог-файл будет называться так же, как модуль, например user_helper.py → logs/user_helper.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

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
        # 1) Принудительное удаление всех старых сообщений
        if forced_delete:
            try:
                qs = SentMessage.objects.filter(telegram_user=user)
                ids = list(qs.values_list("message_id", flat=True))
                bot.delete_messages(user.chat_id, ids)
                qs.delete()
            except Exception:
                SentMessage.objects.filter(telegram_user=user).delete()

        # 2) Последнее отправленное сообщение
        last = SentMessage.objects.filter(telegram_user=user).order_by("-created_at").first()

        # 3) Если нет — просто отправляем новое и сохраняем
        if not last:
            new_msg = send_func()
            SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)
            return new_msg

        chat_id = user.chat_id
        msg_id = last.message_id

        # 4) Пытаемся отредактировать
        try:
            edited = edit_func(chat_id, msg_id)
            return edited
        except ApiException:
            # 5) Если редактирование не удалось — удаляем старое и отправляем новое
            try:
                bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except ApiException:
                pass  # если уже удалено или нельзя удалить

            new_msg = send_func()
            SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)
            return new_msg

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
        # Функция для отправки нового фото
        send_fn = lambda: bot.send_photo(
            chat_id=user.chat_id, photo=photo, caption=caption, **kwargs
        )

        # Функция для редактирования существующего фото
        def edit_fn(chat_id, message_id):
            media = InputMediaPhoto(media=photo, caption=caption)
            sent = bot.edit_message_media(
                chat_id=chat_id, message_id=message_id, media=media
            )
            # Если нужно обновить подпись или клавиатуру, делаем edit_message_caption
            caption_kwargs = {k: v for k, v in kwargs.items() if k in ("reply_markup", "parse_mode")}
            if caption_kwargs:
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
        def menu(user: TelegramUser, forced_delete: bool=False):
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
            text = Messages.MOON_CALC_TODAY.format(date=formatted_date, moon_phase=moon_phase(today_moscow))

            return SendMessages.update_or_replace_last_message(
                user, 
                False,
                text=text, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )

        @staticmethod
        def enter_date(user: TelegramUser):
            return SendMessages.update_or_replace_last_message(
                user, 
                True,
                text=Messages.MOON_CALC_ENTER_DATE, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )
        
        @staticmethod
        def incorrect_enter_date(user: TelegramUser):
            return SendMessages.update_or_replace_last_message(
                user, 
                True,
                text=Messages.MOON_CALC_ENTER_DATE_INCORRECT, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )

        @staticmethod
        def date(user: TelegramUser, date:datetime.datetime):
            formatted_date = date.date().strftime("%d.%m.%Y")
            text = Messages.MOON_CALC_MSG.format(date=formatted_date, moon_phase=moon_phase(date))

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

            Параметры:
                user: экземпляр TelegramUser
                forced_delete: если True — удаляются все прошлые сообщения перед отправкой
            """
            chat_id = user.chat_id

            # Получаем API-ключ из модели-одиночки ApodApiKey
            api_key = ApodApiKey.get_solo().api_key
            try:
                client = APODClient(api_key=api_key)
            except APODClientError as e:
                bot.send_message(chat_id, f"Не удалось инициализировать APOD-клиент: {e}")
                return

            try:
                # 1) Получаем или обновляем запись ApodFile для сегодняшней даты
                apod_obj = client.get_or_update_today()

                # 2) Если media_id уже есть, просто обновляем существующее сообщение с фото
                if apod_obj.telegram_media_id:
                    SendMessages.update_or_replace_last_photo(
                        user=user,
                        forced_delete=True,
                        photo=apod_obj.telegram_media_id,
                        caption=apod_obj.title or ""
                    )
                    return

                # 3) Иначе скачиваем изображение в память
                date_str = apod_obj.date.strftime("%Y-%m-%d")
                image_buffer = client.fetch_image_bytes(date_str)
                image_buffer.seek(0)

                # 4) Отправляем фото, используя helper, и сохраняем новый file_id
                def send_new():
                    return bot.send_photo(chat_id, image_buffer, caption=apod_obj.title or "")

                def edit_existing(chat_id, message_id):
                    media = InputMediaPhoto(media=image_buffer, caption=apod_obj.title or "")
                    sent = bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media)
                    return sent

                SendMessages._update_or_replace_last(
                    user=user,
                    forced_delete=True,
                    send_func=send_new,
                    edit_func=edit_existing
                )

            except APODClientError as e:
                bot.send_message(chat_id, f"Ошибка при получении APOD: {e}")
            except Exception:
                bot.send_message(chat_id, "Произошла внутренняя ошибка при отправке APOD.")



        