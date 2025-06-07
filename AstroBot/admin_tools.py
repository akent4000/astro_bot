from admin_tools.menu import Menu, items

class CustomMenu(Menu):
    """
    Главное меню админки Astro Bot, разделённое на блоки.
    """
    def init_with_context(self, context):
        # APOD
        self.children += [
            items.MenuItem('🚀 APOD', children=[
                items.ModelList(title='API-ключ', models=['tgbot.models.ApodApiKey']),
                items.ModelList(title='Файлы APOD', models=['tgbot.models.ApodFile']),
            ])
        ]
        # Статьи
        self.children += [
            items.MenuItem('📰 Статьи', children=[
                items.ModelList(title='Разделы', models=['tgbot.models.ArticlesSection']),
                items.ModelList(title='Подразделы', models=['tgbot.models.ArticlesSubsection']),
                items.ModelList(title='Статьи', models=['tgbot.models.Article']),
            ])
        ]
        # Настройки бота
        self.children += [
            items.MenuItem('⚙️ Настройки бота', children=[
                items.ModelList(title='Токены ботов', models=['tgbot.models.TelegramBotToken']),
                items.ModelList(title='Конфигурация', models=['tgbot.models.Configuration']),
            ])
        ]
        # Глоссарий
        self.children += [
            items.MenuItem('📖 Глоссарий', children=[
                items.ModelList(models=['tgbot.models.Glossary']),
            ])
        ]
        # Интересные факты
        self.children += [
            items.MenuItem('💡 Интересные факты', children=[
                items.ModelList(title='Факты', models=['tgbot.models.InterestingFact']),
                items.ModelList(title='Подписки', models=['tgbot.models.DailySubscription']),
            ])
        ]
        # SSH & Сервер
        self.children += [
            items.MenuItem('🔑 SSH & Сервер', children=[
                items.ModelList(title='SSH ключи', models=['tgbot.models.SSHKey']),
                items.ModelList(title='Сервер', models=['tgbot.models.Server']),
            ])
        ]
        # Пользователи Telegram
        self.children += [
            items.MenuItem('👤 Пользователи', children=[
                items.ModelList(title='Пользователи', models=['tgbot.models.TelegramUser']),
                items.ModelList(title='Отправленные сообщения', models=['tgbot.models.SentMessage']),
            ])
        ]
        # Квизы
        self.children += [
            items.MenuItem('📚 Квизы', children=[
                items.ModelList(title='Темы', models=['tgbot.models.QuizTopic']),
                items.ModelList(title='Уровни', models=['tgbot.models.QuizLevel']),
                items.ModelList(title='Квизы', models=['tgbot.models.Quiz']),
                items.ModelList(title='Вопросы', models=['tgbot.models.Question']),
                items.ModelList(title='Варианты', models=['tgbot.models.Choice']),
                items.ModelList(title='Сессии', models=['tgbot.models.UserQuizSession']),
                items.ModelList(title='Ответы', models=['tgbot.models.UserQuizAnswer']),
            ])
        ]
        # Администрирование стандартных приложений
        self.children += [
            items.AppList(label='Пользователи и группы', models=['django.contrib.auth.*']),
            items.AppList(label='Системные', models=['django.contrib.*']),
        ]

# В settings.py укажите:
# ADMIN_TOOLS_MENU = 'AstroBot.admin_tools.CustomMenu'
