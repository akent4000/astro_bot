import os

import threading
# 1) Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AstroBot.settings')

# 2) Инициалищируем Django — сразу вызываем ASGI-приложение
from django.core.asgi import get_asgi_application
django_app  = get_asgi_application()

from pathlib import Path
from loguru import logger
# И создаём папку под логи
Path("logs").mkdir(parents=True, exist_ok=True)
logger.add("logs/asgi.log", rotation="10 MB", level="INFO")

from tgbot.startbot import start

async def application(scope, receive, send):
    """
    ASGI router that:
      – on lifespan.startup → kicks off start_bots()
      – on lifespan.shutdown → acks and quits
      – otherwise → delegates to Django’s HTTP/Websocket handlers
    """
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                threading.Thread(target=start, daemon=True).start()
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        # HTTP or WebSocket → hand off to Django
        await django_app(scope, receive, send)