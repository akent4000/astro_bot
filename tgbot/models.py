import json
import os
import uuid
import re
from decimal import Decimal
from django.db import models
from django.db.models import F, QuerySet
from telebot import TeleBot
from django.utils import timezone
from django.core.validators import RegexValidator
import subprocess
from solo.models import SingletonModel
from tgbot.logics.constants import Constants, Messages

from pathlib import Path
from loguru import logger

Path("logs").mkdir(parents=True, exist_ok=True)

log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

telegraph_validator = RegexValidator(
    regex=r'^https?://telegra\.ph/.*$',
    message='Ссылка должна вести на страницу telegra.ph (например: https://telegra.ph/...).',
    code='invalid_telegraph_link'
)

class Configuration(SingletonModel):
    """
    Сингл модель для хранения текущей конфигурации.
    Гарантирует, что в базе будет ровно один объект.
    """
    test_mode = models.BooleanField(
        default=False,
        verbose_name='Включить тестовый режим'
    )

    class Meta:
        verbose_name = 'Конфигурация'
        verbose_name_plural = 'Конфигурация'

    def __str__(self):
        return "Конфигурация бота"

class TelegramBotToken(models.Model):
    """Модель для хранения токена бота"""
    token = models.CharField(max_length=255, verbose_name='Токен бота')
    name = models.CharField(max_length=255, verbose_name='Название бота', default='Bot')
    test_bot = models.BooleanField(default=False, verbose_name='Бот для тестирования')

    def __str__(self):
        return self.name

    @staticmethod
    def get_main_bot_token():
        last_obj = TelegramBotToken.objects.filter(test_bot=False).last()
        return last_obj.token if last_obj else ""

    @staticmethod
    def get_test_bot_token():
        last_obj = TelegramBotToken.objects.filter(test_bot=True).last()
        return last_obj.token if last_obj else ""

    class Meta:
        verbose_name = 'Токен бота'
        verbose_name_plural = 'Токены ботов'


class Server(SingletonModel):
    """
    Сингл модель для хранения параметров сервера.
    В базе всегда будет единственный экземпляр.
    """
    ip = models.CharField(max_length=255, verbose_name='IP сервера')
    password_auth = models.BooleanField(default=False, verbose_name='Разрешить доступ по паролю')
    pubkey_auth = models.BooleanField(default=True, verbose_name='Разрешить доступ по SSH ключу')
    permit_root_login = models.CharField(
        max_length=50,
        default='prohibit-password',
        verbose_name='root логин',
        help_text='Например: yes, no, prohibit-password, forced-commands-only'
    )
    permit_empty_passwords = models.BooleanField(default=False, verbose_name='Разрешить пустые пароли')
    user = models.CharField(default="root", max_length=255, verbose_name='Пользователь SSH')

    class Meta:
        verbose_name = 'Сервер'
        verbose_name_plural = 'Сервер'

    def __str__(self):
        return f"Сервер ({self.ip})"


class SSHKey(models.Model):
    key_name = models.CharField(
        max_length=255,
        verbose_name="Название ключа",
        help_text="Уникальное имя для ключа"
    )
    public_key = models.TextField(
        verbose_name="Публичный ключ",
        help_text="Публичный SSH ключ в формате OpenSSH"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return self.key_name

    class Meta:
        verbose_name = 'SSH ключ'
        verbose_name_plural = 'SSH ключи'


class TelegramUser(models.Model):
    """Модель пользователя Telegram"""
    chat_id = models.BigIntegerField(unique=True, verbose_name='Chat ID')
    first_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Имя')
    last_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Фамилия')
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Username')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    blocked = models.BooleanField(default=False, verbose_name='Блокировка')
    bot_was_blocked = models.BooleanField(default=False, verbose_name='Бот заблокирован')
    send_admin_notifications = models.BooleanField(default=False, verbose_name='Оповещения об ошибках')
    is_admin = models.BooleanField(default=False, verbose_name='Администратор')
    admin_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Подпись администратора',
        help_text='Если пользователь является администратором, эта подпись будет отображаться в сообщениях, отправляемых им.'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} (@{self.username})"

    @staticmethod
    def get_user_by_chat_id(chat_id: int):
        try:
            return TelegramUser.objects.get(chat_id=chat_id)
        except TelegramUser.DoesNotExist:
            return None

    class Meta:
        verbose_name = 'Пользователь Telegram'
        verbose_name_plural = 'Пользователи Telegram'


class SentMessage(models.Model):
    message_id = models.IntegerField(verbose_name='ID сообщения')
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f"{self.telegram_user} - {self.message_id}"

    class Meta:
        verbose_name = 'Отправленное сообщение'
        verbose_name_plural = 'Отправленные сообщения'


class InterestingFact(models.Model):
    link = models.CharField(
        max_length=500,
        verbose_name='Ссылка на факт в telegraph',
        validators=[telegraph_validator],
        help_text='Укажите URL вида https://telegra.ph/...'
    )
    date_to_mailing = models.DateField(
        verbose_name='Дата для рассылки этого факта',
        help_text='Дата и время, когда факт будет отправлен подписчикам'
    )


    class Meta:
        verbose_name = 'Интересный факт'
        verbose_name_plural = 'Интересные факты'

    def __str__(self):
        from tgbot.logics.telegraph_helper import parse_telegraph_title
        return parse_telegraph_title(self.link) or "Без названия"
    
class DailySubscription(models.Model):
    """
    Модель для хранения ежедневной подписки:
    связывает TelegramUser с выбранным временем рассылки.
    """
    user = models.OneToOneField(
        TelegramUser,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="daily_subscription"
    )
    send_time = models.TimeField(
        verbose_name="Время ежедневной рассылки",
        help_text="Укажите время в формате ЧЧ:ММ (например, 08:30)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания подписки"
    )

    class Meta:
        verbose_name = "Ежедневная подписка"
        verbose_name_plural = "Ежедневные подписки"
        ordering = ["send_time"]

    def __str__(self):
        return f"Подписка {self.user} на {self.send_time.strftime('%H:%M')}"

class ArticlesSection(models.Model):
    title = models.CharField(max_length=64, blank=True, null=True, verbose_name='Название раздела статей')

    def __str__(self):
        return self.title or "Раздел без названия"

    class Meta:
        verbose_name = 'Раздел статей'
        verbose_name_plural = 'Разделы статей'


class ArticlesSubsection(models.Model):
    title = models.CharField(max_length=64, blank=True, null=True, verbose_name='Название подраздела статей')
    section = models.ForeignKey(
        ArticlesSection,
        related_name='subsections',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Раздел статьи'
    )

    def __str__(self):
        if self.title:
            return f"{self.section.title or 'Без раздела'} → {self.title}"
        return "Подраздел без названия"

    class Meta:
        verbose_name = 'Подраздел статей'
        verbose_name_plural = 'Подразделы статей'


class Article(models.Model):
    link = models.CharField(
        max_length=500,
        verbose_name='Ссылка на статью в telegraph',
        validators=[telegraph_validator],
        help_text='Укажите URL вида https://telegra.ph/...'
    )
    subsection = models.ForeignKey(
        ArticlesSubsection,
        related_name="articles",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Подраздел статьи'
    )

    def __str__(self):
        from tgbot.logics.telegraph_helper import parse_telegraph_title
        return parse_telegraph_title(self.link) or "Статья без названия"

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'

class QuizTopic(models.Model):
    title = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Название темы квиза',
    )

    class Meta:
        verbose_name = 'Категория тестов'
        verbose_name_plural = 'Категории тестов'

    def __str__(self):
        return self.title

class QuizLevel(models.Model):
    title = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Название категории квиза',
        help_text='Например: Начальный уровень, Средний уровень, Продвинутый'
    )

    class Meta:
        verbose_name = 'Категория тестов'
        verbose_name_plural = 'Категории тестов'

    def __str__(self):
        return self.title


class Quiz(models.Model):
    title = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='Название квиза',
        help_text='Краткое название квиза'
    )
    topic = models.ForeignKey(
        QuizTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quizzes_by_topic',
        verbose_name='Категория теста'
    )
    level = models.ForeignKey(
        QuizLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quizzes_by_level',
        verbose_name='Категория теста'
    )

    class Meta:
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'

    def __str__(self):
        return self.title or f"Тест #{self.pk}"


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='Квиз'
    )
    text = models.TextField(verbose_name='Текст вопроса')
    explanation = models.TextField(
        blank=True,
        null=True,
        verbose_name='Пояснение к вопросу',
        help_text='Краткое пояснение правильного ответа после завершения теста'
    )

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['id']

    def __str__(self):
        return f"{self.text[:50]}..." if len(self.text) > 50 else self.text


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name='Вопрос'
    )
    text = models.CharField(max_length=255, verbose_name='Текст варианта ответа')
    is_correct = models.BooleanField(
        default=False,
        verbose_name='Правильный ответ',
        help_text='Установите True для всех корректных вариантов'
    )

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

    def __str__(self):
        return self.text

class Glossary(SingletonModel):
    link = models.CharField(
        max_length=500,
        verbose_name='Ссылка на глоссарий в telegraph',
        validators=[telegraph_validator],
        help_text='Укажите URL вида https://telegra.ph/...'
    )

    class Meta:
        verbose_name = 'Глоссарий'
        verbose_name_plural = 'Глоссарий'

    def __str__(self):
        return self.link or ""

class ApodApiKey(SingletonModel):
    api_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='API ключ для доступа к NASA APOD API',
    )

    class Meta:
        verbose_name = 'APOD API ключ'
        verbose_name_plural = 'APOD API ключ'

    def __str__(self):
        return self.api_key or ""

class ApodFile(models.Model):
    """
    Модель для хранения метаданных APOD (Astronomy Picture of the Day) и telegram_media_id,
    чтобы не загружать изображение заново, если оно уже отправлено в Telegram.
    """
    date = models.DateField(
        unique=True,
        verbose_name="Дата APOD",
        help_text="Дата снимка в формате ГГГГ-ММ-ДД"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Заголовок"
    )
    explanation = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    telegram_media_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Telegram media_id",
        help_text="ID изображения, полученный при отправке в Telegram"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата добавления"
    )

    class Meta:
        verbose_name = "APOD-файл"
        verbose_name_plural = "APOD-файлы"
        ordering = ["-date"]

    def __str__(self):
        return f"APOD {self.date} — {self.title or 'Без названия'}"
    
