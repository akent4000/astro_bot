# tgbot/dispatcher.py

import logging
from pathlib import Path

from tgbot.syncbot import SyncBot
from tgbot.models import Configuration, TelegramBotToken

# Настраиваем логгирование dispatcher’а
Path("logs").mkdir(parents=True, exist_ok=True)
log_filename = Path("logs") / "dispatcher.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger("dispatcher")

# Внутренние хранилища экземпляров ботов
_main_bot: SyncBot | None = None
_test_bot: SyncBot | None = None


def _initialize_bot(token: str) -> SyncBot:
    """
    Вспомогательная функция, которая создаёт SyncBot и сразу
    регистрирует у него все команды из tgbot.logics.commands.init_bot_commands.
    """
    bot = SyncBot(token)
    try:
        # Импортируем и устанавливаем команды именно здесь, когда бот уже создан
        from tgbot.logics.commands import init_bot_commands
        init_bot_commands(bot)
        logger.info("Commands initialized for bot with token ending in …%s", token[-6:])
    except Exception as e:
        logger.exception("Failed to initialize bot commands: %s", e)
    return bot


def get_main_bot() -> SyncBot:
    """
    Возвращает «главный» бот (SyncBot), инициализируя его при первом вызове.
    Если в Configuration.test_mode включен тестовый режим, токены меняются местами.
    """
    global _main_bot

    if _main_bot is not None:
        return _main_bot

    # Сначала читаем «основной» и «тестовый» токены
    main_token = TelegramBotToken.get_main_bot_token()
    test_token = TelegramBotToken.get_test_bot_token()

    try:
        config = Configuration.get_solo()
        if config.test_mode:
            if test_token:
                main_token = test_token
                logger.info("Test mode enabled — swapped main and test tokens.")
            else:
                logger.warning("Test mode enabled, but test_token is empty → using main_token unchanged.")
    except Exception:
        # Если Configuration ещё не создана, просто логируем и продолжаем с base-токеном
        logger.warning("Cannot fetch Configuration singleton; proceeding with main_token as is.")

    if not main_token:
        raise RuntimeError("Main bot token is not defined in TelegramBotToken table.")

    _main_bot = _initialize_bot(main_token)
    logger.info("Main SyncBot instance created.")
    return _main_bot


def get_test_bot() -> SyncBot:
    """
    Возвращает «главный» бот (SyncBot), инициализируя его при первом вызове.
    Если в Configuration.test_mode включен тестовый режим, токены меняются местами.
    """
    global _test_bot

    if _test_bot is not None:
        return _test_bot

    # Сначала читаем «основной» и «тестовый» токены
    main_token = TelegramBotToken.get_main_bot_token()
    test_token = TelegramBotToken.get_test_bot_token()

    try:
        config = Configuration.get_solo()
        if config.test_mode:
            if test_token:
                test_token = main_token
                logger.info("Test mode enabled — swapped main and test tokens.")
            else:
                logger.warning("Test mode enabled, but test_token is empty → using main_token unchanged.")
    except Exception:
        # Если Configuration ещё не создана, просто логируем и продолжаем с base-токеном
        logger.warning("Cannot fetch Configuration singleton; proceeding with main_token as is.")

    if not test_token:
        raise RuntimeError("Main bot token is not defined in TelegramBotToken table.")

    _test_bot = _initialize_bot(test_token)
    logger.info("Test SyncBot instance created.")