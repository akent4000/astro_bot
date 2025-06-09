from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest
from telebot import types
from tgbot.bot_instances import instances
from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

@csrf_exempt
def telegram_webhook(request, hook_id: int):
    bot = instances.get(hook_id)
    if not bot:
        return HttpResponseBadRequest('Unknown bot ID')
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')
    body = request.body.decode('utf-8')
    try:
        update = types.Update.de_json(body)
    except Exception:
        return HttpResponseBadRequest('Invalid update')
    bot.process_new_updates([update])
    return HttpResponse('OK')