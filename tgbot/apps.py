from django.apps import AppConfig

class TgbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tgbot'

    def ready(self):
        import tgbot.signals
        import tgbot.handlers.commands
        import tgbot.handlers.main_menu
        import tgbot.handlers.moon_calc
        import tgbot.handlers.apod
        import tgbot.handlers.int_facts
        import tgbot.handlers.articles
        import tgbot.handlers.quzzes