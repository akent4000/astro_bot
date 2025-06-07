# tgbot/logics/messages.py

import time
import re
from typing import Optional, Iterable, Union

import requests

from tgbot.dispatcher import get_main_bot
bot = get_main_bot()

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
                True,
                text=Messages.MOON_CALC,
                reply_markup=Keyboards.MoonCalc.menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def today(user: TelegramUser):
            today_moscow = datetime.datetime.now(ZoneInfo(Constants.ZONE_INFO)).date()
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
            Логика сведена к одному вызову update_or_replace_last_photo:
            - Если telegram_media_id уже есть, photo=telegram_media_id.
            - Если нет, скачиваем новый буфер и передаём его.
            После отправки (если file_id был пуст) сохраняем новый telegram_media_id.
            """
            chat_id = user.chat_id
            logger.debug(f"Apod.send_apod: user={user}")

            # 1) Берём API-ключ из Singleton-модели
            api_key = ApodApiKey.get_solo().api_key
            if not api_key:
                logger.error("Apod.send_apod: отсутствует API-ключ ApodApiKey")
                bot.send_message(chat_id, "API-ключ APOD не задан.")
                return

            # 2) Инициализируем клиент
            try:
                client = APODClient(api_key=api_key)
                logger.info("Apod.send_apod: APODClient успешно инициализирован")
            except APODClientError as e:
                logger.error(f"Apod.send_apod: ошибка инициализации APODClient: {e}")
                bot.send_message(chat_id, f"Не удалось инициализировать APOD-клиент: {e}")
                return

            try:
                # 3) Получаем или создаём ApodFile для сегодняшнего дня (объект date — datetime.date)
                apod_obj = client.get_or_update_today()
                logger.info(f"Apod.send_apod: получен ApodFile(date={apod_obj.date}, media_id={apod_obj.telegram_media_id})")

                # 4) Решаем, что передавать в send_photo:
                #    если telegram_media_id уже есть — используем его (просто обновится caption/клавиатура),
                #    иначе скачиваем картинку в память.
                if apod_obj.telegram_media_id:
                    photo_source = apod_obj.telegram_media_id
                    logger.debug("Apod.send_apod: Используем existing file_id для photo_source")
                else:
                    date_str = apod_obj.date.strftime("%Y-%m-%d")
                    logger.info(f"Apod.send_apod: Скачиваем изображение для {date_str}")
                    image_buffer = client.fetch_image_bytes(date_str)
                    image_buffer.seek(0)
                    photo_source = image_buffer
                    logger.debug("Apod.send_apod: Буфер с изображением сформирован, переход к отправке")

                # 5) Один раз вызываем update_or_replace_last_photo. 
                #    forced_delete=True — чтобы удалить предыдущее APOD‐сообщение.
                #    caption=заголовок, reply_markup=клавиатура «назад в меню».
                result_msg = SendMessages.update_or_replace_last_photo(
                    user=user,
                    forced_delete=True,
                    photo=photo_source,
                    caption=apod_obj.title or "",
                    reply_markup=Keyboards.Apod.back_to_menu(),
                    parse_mode="Markdown"
                )

                # 6) Если ранее не было telegram_media_id, надо сохранить новый file_id:
                if not apod_obj.telegram_media_id:
                    # Telegram возвращает list объектов PhotoSize; последний имеет актуальный file_id
                    try:
                        new_file_id = result_msg.photo[-1].file_id
                        apod_obj.telegram_media_id = new_file_id
                        apod_obj.save(update_fields=["telegram_media_id"])
                        logger.info(f"Apod.send_apod: сохранён новый telegram_media_id={new_file_id}")
                    except Exception as e:
                        # На случай, если result_msg оказался не фотографией
                        logger.error(f"Apod.send_apod: не удалось сохранить новый file_id: {e}")

            except APODClientError as e:
                logger.error(f"Apod.send_apod: ошибка при получении APOD: {e}")
                bot.send_message(chat_id, f"Ошибка при получении APOD: {e}")

            except Exception:
                logger.exception("Apod.send_apod: внутренняя ошибка при отправке APOD")
                bot.send_message(chat_id, "Произошла внутренняя ошибка при отправке APOD.")

    class IntFacts:
        @staticmethod
        def menu(user: TelegramUser):
            logger.debug(f"IntFacts.menu: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.INT_FACTS,
                reply_markup=Keyboards.IntFacts.menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def today(user: TelegramUser, forced_delete: bool = False):
            today_moscow = datetime.datetime.now(ZoneInfo(Constants.ZONE_INFO)).date()
            fact = InterestingFact.objects.filter(date_to_mailing=today_moscow).first()
            if fact is None:
                text = Messages.INT_FACTS_FACT_TODAY_NOT_FOUND
            else:
                text = Messages.INT_FACTS_FACT.format(id=fact.id)

            logger.debug(f"IntFacts.today: user={user}, fact={fact}")

            return SendMessages.update_or_replace_last_message(
                user,
                forced_delete,
                text=text,
                reply_markup=Keyboards.IntFacts.today(fact),
                parse_mode="Markdown"
            )
        
        @staticmethod
        def choose_time_or_default(user: TelegramUser):
            logger.debug(f"IntFacts.enter_time: user={user}")
            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=Messages.INT_FACTS_CHOOSE_ENTER_OR_DEFAULT,
                reply_markup=Keyboards.IntFacts.choose_time_or_default(),
                parse_mode="Markdown"
            )

        @staticmethod
        def enter_time(user: TelegramUser):
            logger.debug(f"IntFacts.enter_time: user={user}")
            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=Messages.INT_FACTS_FACT_ENTER_TIME,
                reply_markup=Keyboards.IntFacts.back_and_main_menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def incorrect_enter_time(user: TelegramUser):
            logger.debug(f"IntFacts.incorrect_enter_time: user={user}")
            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=Messages.INT_FACTS_FACT_ENTER_TIME_INCORRECT,
                reply_markup=Keyboards.IntFacts.back_enter_time_and_main_menu(),
                parse_mode="Markdown"
            )

        @staticmethod
        def sub(user: TelegramUser, time: datetime.time):
            formatted_time = time.strftime("%H:%M")
            text = Messages.INT_FACTS_SUB.format(time=formatted_time)
            logger.debug(f"IntFacts.sub: user={user}, time={formatted_time}")

            return SendMessages.update_or_replace_last_message(
                user,
                True,
                text=text,
                reply_markup=Keyboards.IntFacts.back_and_main_menu(),
                parse_mode="Markdown"
            )
        
        @staticmethod
        def unsub(user: TelegramUser):
            logger.debug(f"IntFacts.unsub: user={user}")

            return SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.INT_FACTS_UNSUB,
                reply_markup=Keyboards.IntFacts.back_and_main_menu(),
                parse_mode="Markdown"
            )
        
    class Articles:
        @staticmethod
        def choose_section(user: TelegramUser):
            logger.debug(f"Articles.choose_section: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.ARTICLES_SECTION,
                reply_markup=Keyboards.Articles.choose_section(),
                parse_mode="Markdown"
            )
        
        @staticmethod
        def choose_subsection(user: TelegramUser, article_section: ArticlesSection):
            logger.debug(f"Articles.choose_section: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.ARTICLES_SUBSECTION,
                reply_markup=Keyboards.Articles.choose_subsection(article_section),
                parse_mode="Markdown"
            )

        @staticmethod
        def choose_article(user: TelegramUser, article_subsection: ArticlesSubsection):
            logger.debug(f"Articles.choose_article: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.ARTICLES_ARTICLE,
                reply_markup=Keyboards.Articles.choose_article(article_subsection),
                parse_mode="Markdown"
            )
    
    class Quizzes:
        @staticmethod
        def choose_topic(user: TelegramUser):
            logger.debug(f"Quizzes.choose_topic: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.QUIZZES_TOPIC,
                reply_markup=Keyboards.Quizzes.choose_topic(),
                parse_mode="Markdown"
            )
        
        @staticmethod
        def choose_level(user: TelegramUser, quiz_topic: QuizTopic):
            logger.debug(f"Quizzes.choose_level: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.QUIZZES_LEVEL,
                reply_markup=Keyboards.Quizzes.choose_level(quiz_topic),
                parse_mode="Markdown"
            )

        @staticmethod
        def choose_quiz(user: TelegramUser, quiz_topic: QuizTopic, quiz_level: QuizLevel):
            logger.debug(f"Quizzes.choose_quiz: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.QUIZZES_QUIZ,
                reply_markup=Keyboards.Quizzes.choose_quiz(quiz_topic, quiz_level),
                parse_mode="Markdown"
            )

        @staticmethod
        def question(user: TelegramUser, question: Question, session: UserQuizSession):
            logger.debug(f"Quizzes.question: user={user}")
            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=Messages.QUIZZES_QUIZ_QUESTION.format(n=question.order+1, description=question.text),
                reply_markup=Keyboards.Quizzes.question(question, session),
                parse_mode="Markdown"
            )
        
        @staticmethod
        def end(user: TelegramUser, session: UserQuizSession):
            logger.debug(f"Quizzes.end: user={user}")
            text = Messages.QUIZZES_QUIZ_END.format(n=session.score(), n_questions=session.quiz.question_count)

            for question in session.quiz.questions.all():
                text += Messages.QUIZZES_QUIZ_QUESTION_EXPLANATION.format(
                    question=Messages.QUIZZES_QUIZ_QUESTION.format(n=question.order+1, description=question.text),
                    user_choice=session.answers.filter(question=question).first().choice.text,
                    choice=question.choices.filter(is_correct=True).first().text,
                    explanation=question.explanation,
                )

            SendMessages.update_or_replace_last_message(
                user,
                False,
                text=text,
                reply_markup=Keyboards.Quizzes.end(session),
                parse_mode="Markdown"
            )