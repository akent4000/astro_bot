from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from telebot import types
from tgbot.bot_instances import bots
from django.shortcuts import render
import json

from pathlib import Path
from loguru import logger

Path("logs").mkdir(parents=True, exist_ok=True)

log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

def home(request):
    return render(request, 'index.html')

@csrf_exempt
def telegram_webhook(request, hook_id):
    """
    Обрабатывает POST от Telegram:
    - hook_id: число в URL, по которому ищем нужный TeleBot в instances
    """
    # 1) Найти бот по переданному ID
    try:
        bot = bots[int(hook_id)]
    except (KeyError, ValueError):
        logger.warning(f"Webhook: неизвестный hook_id {hook_id}")
        return HttpResponseBadRequest("Unknown bot ID")

    # 2) Убедиться, что метод POST
    if request.method != "POST":
        logger.warning(f"Webhook({hook_id}): неверный метод {request.method}")
        return HttpResponseBadRequest("Invalid method, use POST")

    # 3) Распарсить JSON
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"Webhook({hook_id}): невалидный JSON: {e}")
        return HttpResponseBadRequest("Invalid JSON")

    # 4) Превратить dict в Update
    try:
        update = types.Update.de_json(payload)
    except Exception as e:
        logger.exception(f"Webhook({hook_id}): ошибка разбора Update: {e}")
        return HttpResponseBadRequest("Invalid update")

    # 5) Передать апдейт в TeleBot
    try:
        bot.process_new_updates([update])
    except Exception as e:
        logger.exception(f"Webhook({hook_id}): ошибка обработки апдейта: {e}")
        # всё равно возвращаем 200, чтобы Telegram не пытался резендить бесконечно
        return HttpResponse("OK")

    return HttpResponse("OK")