import os
from decimal import Decimal

from django.db.models.signals import *
from django.db import transaction
from django.dispatch import receiver
from telebot.apihelper import ApiTelegramException
import time
from tgbot.models import *
from tgbot.managers.ssh_manager import SSHAccessManager, sync_keys
import threading
from django.core.cache import cache
import time
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например user_helper.py → logs/user_helper.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

@receiver(pre_save, sender=Server)
def server_pre_save(sender, instance, **kwargs):
    """
    На pre_save кладём в instance._old_instance прежний вариант (если он есть).
    Если instance.pk is None (новый объект), просто запоминаем old_instance = None.
    """
    if instance.pk is None:
        # первый сохранённый экземпляр – старой версии нет
        instance._old_instance = None
    else:
        try:
            instance._old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._old_instance = None


@receiver(post_save, sender=Server)
def server_post_save(sender, instance, created, **kwargs):
    """
    После сохранения (post_save) смотрим, какие поля изменились.
    Если changed_fields содержит 'user' — синхронизируем ключи с задержкой при создании,
    либо убираем/пересоздаём их сразу при обновлении.
    Также, если создан новый объект или изменились SSH-параметры, вызываем set_auth_methods.
    """
    # Определим список изменённых полей
    changed_fields = []

    if created or instance._old_instance is None:
        # если только что создали, считаем все поля «изменёнными»
        changed_fields = [field.name for field in instance._meta.fields]
    else:
        old = instance._old_instance
        for field in instance._meta.fields:
            name = field.name
            old_value = getattr(old, name)
            new_value = getattr(instance, name)
            if old_value != new_value:
                changed_fields.append(name)

    # Если изменилось поле 'user'
    if 'user' in changed_fields:
        if created:
            # При создании – через 30 секунд запускаем sync_keys(), потому что
            # сетевые/SSH-операции могут требовать, чтобы система успела «подумать»
            timer = threading.Timer(30, sync_keys)
            timer.start()
        else:
            # При обновлении – сначала удалим старые ключи, потом синхронизируем
            old_user = instance._old_instance.user if instance._old_instance else None
            if old_user:
                manager = SSHAccessManager()
                current_keys = set(manager.get_ssh_keys(old_user))
                for key in current_keys:
                    manager.remove_ssh_key(old_user, key)
            sync_keys()

    # Поля, отвечающие за SSH-аутентификацию:
    auth_fields = [
        'password_auth',
        'pubkey_auth',
        'permit_root_login',
        'permit_empty_passwords'
    ]

    # Если создали новый или изменились настройки аутентификации – вызываем set_auth_methods
    if created or any(f in changed_fields for f in auth_fields):
        password_auth = instance.password_auth
        pubkey_auth = instance.pubkey_auth
        permit_root_login = instance.permit_root_login
        permit_empty_passwords = instance.permit_empty_passwords

        # new_password_for_user мы не храним в модели, предполагаем, что его установит кто-то отдельно
        new_password_for_user = None

        manager = SSHAccessManager()

        if created:
            timer = threading.Timer(
                30,
                lambda: manager.set_auth_methods(
                    password_auth,
                    pubkey_auth,
                    permit_root_login,
                    permit_empty_passwords,
                    new_password_for_user
                )
            )
            timer.start()
        else:
            manager.set_auth_methods(
                password_auth,
                pubkey_auth,
                permit_root_login,
                permit_empty_passwords,
                new_password_for_user
            )
            


@receiver(pre_save, sender=Configuration)
def configuration_pre_save(sender, instance, **kwargs):
    """
    Перед сохранением сохраняем старое значение test_mode
    в instance._old_test_mode, чтобы потом понять, поменялось ли оно.
    """
    if not instance.pk:
        # ещё нет записи в БД — это первая сохранёнка
        instance._old_test_mode = None
    else:
        try:
            old = Configuration.objects.get(pk=instance.pk)
            instance._old_test_mode = old.test_mode
        except Configuration.DoesNotExist:
            instance._old_test_mode = None

def _swap_bots():
    try:
        from tgbot.dispatcher import get_main_bot, get_test_bot
        test_mode = Configuration.get_solo().test_mode
        main_bot_url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.MAIN_BOT_WH_I)
        test_bot_url = Constants.BOT_WEBHOOCK_URL.format(i=Constants.TEST_BOT_WH_I)

        bot = get_main_bot(True)
        test_bot = get_test_bot(True)
        
        bot.remove_webhook()
        test_bot.remove_webhook()

        max_retries = 3
        for attempt in range(1, max_retries+1):
            try:
                bot.remove_webhook()
                test_bot.remove_webhook()
                bot.set_webhook(url=main_bot_url if test_mode else test_bot_url)
                test_bot.set_webhook(url=test_bot_url if test_mode else main_bot_url)

                logger.info("Webhook установлен в воркере PID %s", os.getpid())
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = e.result_json.get("parameters", {}).get("retry_after", 1)
                    logger.warning("429 retry after %s", retry_after)
                    time.sleep(retry_after)
                    continue
                else:
                    logger.exception("Ошибка set_webhook: %s", e)
                    break
        
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Failed to restart service 'bot'. Return code: {e.returncode}. "
            f"stdout:\n{e.stdout.strip()}\nstderr:\n{e.stderr.strip()}"
        )
    except Exception as e:
        logger.exception("Unexpected error while trying to restart 'bot' service:")

@receiver(post_save, sender=Configuration)
def configuration_post_save(sender, instance, created, **kwargs):
    old = getattr(instance, '_old_test_mode', None)
    new = instance.test_mode

    if created or (old is not None and old != new):
        # вместо spawn-а одного потока, просто обновляем метку
        cache.set("tgbot_config_changed", time.time())  

@receiver(post_save, sender=TelegramBotToken)
def tgbot_token_post_save(sender, instance, created, **kwargs):
    def _deferred():
        # запускаем в отдельном потоке, чтобы не блокировать процесс Django
        threading.Thread(target=_swap_bots, daemon=True).start()

    transaction.on_commit(_deferred)