from tgbot.syncbot import SyncBot
from tgbot.models import Configuration, TelegramBotToken
from tgbot.logics.commands import init_bot_commands

from pathlib import Path
from loguru import logger


# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например user_helper.py → logs/user_helper.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")
logger.add("logs/dispatcher.log", rotation="10 MB", level="INFO")

main_bot_token = TelegramBotToken.get_main_bot_token()
test_bot_token = TelegramBotToken.get_test_bot_token()

# Подмена токенов в тестовом режиме
if Configuration.get_solo().test_mode:
    if test_bot_token:
        main_bot_token, test_bot_token = test_bot_token, main_bot_token
        logger.info("Running in test mode — tokens swapped.")
    else:
        logger.warning("Running in test mode, but test token is missing. Using main token as is.")

# Инициализация ботов
bot = SyncBot(main_bot_token)
logger.info("Main bot instance created")

# Установка команд
init_bot_commands(bot)
logger.info("Bot commands initialized")

# Тестовый бот может отсутствовать
test_bot = None
if test_bot_token:
    test_bot = SyncBot(test_bot_token)
    init_bot_commands(test_bot)
    logger.info("Test bot instance created")
else:
    logger.warning("Test bot token not provided — test_bot is not initialized.")
