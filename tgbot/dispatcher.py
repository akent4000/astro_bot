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
    logger.debug("_initialize_bot: вход с токеном, оканчивающимся на …%s", token[-6:])
    bot = SyncBot(token)
    try:
        # Импортируем и устанавливаем команды именно здесь, когда бот уже создан
        from tgbot.logics.commands import init_bot_commands

        init_bot_commands(bot)
        logger.info("Commands initialized for bot with token ending in …%s", token[-6:])
    except Exception as e:
        logger.exception("Failed to initialize bot commands: %s", e)
    logger.debug("_initialize_bot: выход, возвращаем экземпляр SyncBot")
    return bot


def get_main_bot(clear=False) -> SyncBot:
    """
    Возвращает «главный» бот (SyncBot), инициализируя его при первом вызове.
    Если в Configuration.test_mode включен тестовый режим, токены меняются местами.
    """
    global _main_bot

    if _main_bot is not None and not clear:
        logger.debug("get_main_bot: возвращаем ранее созданный экземпляр")
        return _main_bot

    logger.debug("get_main_bot: экземпляр ещё не создан, начинаем инициализацию")
    # Сначала читаем «основной» и «тестовый» токены
    main_token = TelegramBotToken.get_main_bot_token()
    test_token = TelegramBotToken.get_test_bot_token()
    logger.info("get_main_bot: получены токены — main_token есть: %s, test_token есть: %s", bool(main_token), bool(test_token))

    try:
        config = Configuration.get_solo()
        logger.info("get_main_bot: прочитана конфигурация test_mode=%s", config.test_mode)
        if config.test_mode:
            if test_token:
                main_token = test_token
                logger.info("get_main_bot: test_mode включен — main_token заменён на test_token")
            else:
                logger.warning("get_main_bot: test_mode включен, но test_token пуст — main_token не меняется")
    except Exception:
        logger.warning("get_main_bot: не удалось получить Configuration — используем main_token без изменений")

    if not main_token:
        logger.error("get_main_bot: main_token не определён в таблице TelegramBotToken")
        raise RuntimeError("Main bot token is not defined in TelegramBotToken table.")

    _main_bot = _initialize_bot(main_token)
    logger.info("get_main_bot: создан основной SyncBot instance")
    return _main_bot


def get_test_bot(clear=False) -> SyncBot:
    """
    Возвращает «тестовый» бот (SyncBot), инициализируя его при первом вызове.
    Если в Configuration.test_mode включен тестовый режим, токены меняются местами.
    """
    global _test_bot

    if _test_bot is not None and not clear:
        logger.debug("get_test_bot: возвращаем ранее созданный экземпляр")
        return _test_bot

    logger.debug("get_test_bot: экземпляр ещё не создан, начинаем инициализацию")
    # Сначала читаем «основной» и «тестовый» токены
    main_token = TelegramBotToken.get_main_bot_token()
    test_token = TelegramBotToken.get_test_bot_token()
    logger.info("get_test_bot: получены токены — main_token есть: %s, test_token есть: %s", bool(main_token), bool(test_token))

    try:
        config = Configuration.get_solo()
        logger.info("get_test_bot: прочитана конфигурация test_mode=%s", config.test_mode)
        if config.test_mode:
            if test_token:
                # При тестовом режиме swap: тестовый бот получает основной токен
                test_token = main_token
                logger.info("get_test_bot: test_mode включен — swap main и test токенов для тестового бота")
            else:
                logger.warning("get_test_bot: test_mode включен, но test_token пуст — используем main_token как test_token")
    except Exception:
        logger.warning("get_test_bot: не удалось получить Configuration — используем test_token без изменений")

    if not test_token:
        logger.error("get_test_bot: test_token не определён в таблице TelegramBotToken")
        raise RuntimeError("Test bot token is not defined in TelegramBotToken table.")

    _test_bot = _initialize_bot(test_token)
    logger.info("get_test_bot: создан тестовый SyncBot instance")
    return _test_bot
