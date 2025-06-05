import time
import re
from typing import Optional, Iterable, Union

from tgbot.dispatcher import bot

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
    def update_or_replace_last_message(user: TelegramUser, text: str, **kwargs):
        """
        Пытается изменить последнее отправленное пользователю сообщение.
        Если редактирование не удалось (например, сообщение уже не редактируется),
        удаляет старое и отправляет новое.
        
        Параметры:
            user: экземпляр TelegramUser, которому нужно обновить сообщение.
            text: новый текст сообщения (передается в edit_message_text или send_message).
            **kwargs: любые дополнительные аргументы для методов bot.edit_message_text / bot.send_message,
                    например reply_markup, parse_mode и т.д.
        """
        # Получаем последнее отправленное сообщение
        last_sent = SentMessage.objects.filter(telegram_user=user).order_by('-created_at').first()
        
        # Если нет предыдущих сообщений, просто отправляем новое
        if not last_sent:
            new_msg = bot.send_message(chat_id=user.chat_id, text=text, **kwargs)
            SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)
            return

        chat_id = user.chat_id
        message_id = last_sent.message_id

        try:
            # Пытаемся отредактировать текст последнего сообщения
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **kwargs
            )
        except ApiException:
            # Если не получилось редактировать (например, сообщение удалено или слишком старое),
            # удаляем старое и отправляем новое.
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except ApiException:
                # Игнорируем ошибку удаления, если сообщение уже удалено
                pass

            new_msg = bot.send_message(chat_id=chat_id, text=text, **kwargs)
            SentMessage.objects.create(telegram_user=user, message_id=new_msg.message_id)


    class MainMenu:
        @staticmethod
        def menu(user: TelegramUser):
            SendMessages.update_or_replace_last_message(
                user, 
                text=Messages.MENU_MESSAGE,
                reply_markup=Keyboards.MainMenu.menu(), 
                parse_mode="Markdown"
            )

    class MoonCalc:
        @staticmethod
        def menu(user: TelegramUser):
            SendMessages.update_or_replace_last_message(
                user, 
                text=Messages.MOON_CALC, 
                reply_markup=Keyboards.MoonCalc.menu(), 
                parse_mode="Markdown"
            )
        
        @staticmethod
        def today(user: TelegramUser):
            moscow_tz = ZoneInfo('Europe/Moscow')
            today_moscow = datetime.now(moscow_tz).date()
            formatted_date = today_moscow.strftime("%d.%m.%Y")
            text = Messages.MOON_CALC_TODAY.format(date=formatted_date, moon_phase=moon_phase(today_moscow))

            SendMessages.update_or_replace_last_message(
                user, 
                text=text, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )

        @staticmethod
        def enter_date(user: TelegramUser):
            SendMessages.update_or_replace_last_message(
                user, 
                text=Messages.MOON_CALC_ENTER_DATE, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )

        @staticmethod
        def date(user: TelegramUser, date:datetime.datetime):
            formatted_date = date.date().strftime("%d.%m.%Y")
            text = Messages.MOON_CALC_TODAY.format(date=formatted_date, moon_phase=moon_phase(date))

            SendMessages.update_or_replace_last_message(
                user, 
                text=text, 
                reply_markup=Keyboards.MoonCalc.back_and_main_menu(), 
                parse_mode="Markdown"
            )

    