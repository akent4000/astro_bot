from tgbot.logics.telegraph_helper import parse_telegraph_title
from tgbot.models import ArticlesSection, ArticlesSubsection, Choice, Glossary, InterestingFact, Question, QuizTopic, QuizLevel, Quiz, UserQuizSession
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from tgbot.logics.constants import *
from urllib.parse import urlencode
from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например user_helper.py → logs/user_helper.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="INFO")

class Keyboards:
    @staticmethod
    def build_callback_data(base: str, params: dict[str, str] = None) -> str:
        """
        Формирует callback_data в формате URL-подобной строки.

        Аргументы:
            base: базовая строка callback_data (без “?” и параметров)
            params: словарь параметров вида {"первый": "знач1", "второй": "знач2", ...}

        Возвращает:
            Если params пуст или None, возвращает просто base.
            Иначе – строку "base?ключ1=знач1&ключ2=знач2&…", где ключи и значения URL-кодируются.
        """
        if not params:
            return base

        # urlencode автоматически экранирует пробелы, кириллицу и спецсимволы
        query = urlencode(params, doseq=True)
        return f"{base}?{query}"
    
    @staticmethod
    def _add_back(markup: InlineKeyboardMarkup, back_callback: str):
        back_btn = InlineKeyboardButton(text=ButtonNames.BACK, callback_data=back_callback)
        markup.add(back_btn)
        return markup

    @staticmethod
    def _add_menu(markup: InlineKeyboardMarkup):
        menu_btn = InlineKeyboardButton(text=ButtonNames.MENU, callback_data=CallbackData.MENU)
        markup.add(menu_btn)
        return markup
    
    @staticmethod
    def _add_menu_forced_delete(markup: InlineKeyboardMarkup):
        menu_btn = InlineKeyboardButton(text=ButtonNames.MENU, callback_data=CallbackData.MENU_FORCED_DELETE)
        markup.add(menu_btn)
        return markup

    class MainMenu:
        @staticmethod
        def menu():
            markup = InlineKeyboardMarkup()

            moon_calc = InlineKeyboardButton(
                text=ButtonNames.MOON_CALC,
                callback_data=CallbackData.MOON_CALC
            )
            int_facts = InlineKeyboardButton(
                text=ButtonNames.INT_FACTS,
                callback_data=CallbackData.INT_FACTS
            )
            apod = InlineKeyboardButton(
                text=ButtonNames.APOD,
                callback_data=CallbackData.APOD
            )
            articles = InlineKeyboardButton(
                text=ButtonNames.ARTICLES,
                callback_data=CallbackData.ARTICLES
            )
            quizzes = InlineKeyboardButton(
                text=ButtonNames.QUIZZES,
                callback_data=CallbackData.QUIZZES
            )
            glossary = InlineKeyboardButton(
                text=ButtonNames.GLOSSARY,
                url=Glossary.get_solo().link
            )

            markup.add(moon_calc)
            markup.add(int_facts)
            markup.add(apod)
            markup.add(articles)
            markup.add(quizzes)
            markup.add(glossary)

            return markup

    class MoonCalc:
        @staticmethod
        def menu():
            markup = InlineKeyboardMarkup()

            today = InlineKeyboardButton(
                text=ButtonNames.TODAY,
                callback_data=CallbackData.MOON_CALC_TODAY
            )
            enter_date = InlineKeyboardButton(
                text=ButtonNames.ENTER_DATE,
                callback_data=CallbackData.MOON_CALC_ENTER_DATE
            )

            markup.add(today)
            markup.add(enter_date)

            return Keyboards._add_menu(markup)
        
        @staticmethod
        def back_and_main_menu():
            markup = InlineKeyboardMarkup()
            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.MOON_CALC))
        
    class IntFacts:
        @staticmethod
        def menu():
            markup = InlineKeyboardMarkup()

            today = InlineKeyboardButton(
                text=ButtonNames.TODAY,
                callback_data=CallbackData.INT_FACTS_TODAY
            )
            sub = InlineKeyboardButton(
                text=ButtonNames.INT_FACTS_SUB,
                callback_data=CallbackData.INT_FACTS_SUB
            )
            unsub = InlineKeyboardButton(
                text=ButtonNames.INT_FACTS_UNSUB,
                callback_data=CallbackData.INT_FACTS_UNSUB
            )

            markup.add(today)
            markup.add(sub)
            markup.add(unsub)

            return Keyboards._add_menu(markup)

        @staticmethod
        def today(int_fact: InterestingFact):
            markup = InlineKeyboardMarkup()
            
            if int_fact is not None:
                link = InlineKeyboardButton(
                    text=parse_telegraph_title(int_fact.link),
                    callback_data=CallbackData.INT_FACTS_TODAY,
                    url=int_fact.link
                )
                markup.add(link)

            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.INT_FACTS))
        
        @staticmethod
        def choose_time_or_default():
            markup = InlineKeyboardMarkup()

            default_time = InlineKeyboardButton(
                text=ButtonNames.INT_FACTS_DEFAULT_TIME,
                callback_data=CallbackData.INT_FACTS_DEFAULT_TIME
            )
            enter_time = InlineKeyboardButton(
                text=ButtonNames.ENTER_TIME,
                callback_data=CallbackData.INT_FACTS_ENTER_TIME
            )
            markup.add(default_time)
            markup.add(enter_time)

            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.INT_FACTS))

        
        @staticmethod
        def back_and_main_menu():
            markup = InlineKeyboardMarkup()
            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.INT_FACTS))

        
        @staticmethod
        def back_enter_time_and_main_menu():
            markup = InlineKeyboardMarkup()
            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.INT_FACTS_ENTER_TIME))

        
    class Apod:
        @staticmethod
        def back_to_menu():
            markup = InlineKeyboardMarkup()
            return Keyboards._add_menu_forced_delete(markup)

        
    class Articles:
        @staticmethod
        def choose_section():
            sections = ArticlesSection.objects.all()
            markup = InlineKeyboardMarkup()

            for section in sections:
                callback = Keyboards.build_callback_data(CallbackData.ARTICLES_SECTION, {CallbackData.ARTICLES_SECTION_ID: section.id})
                btn = InlineKeyboardButton(text=section.title, callback_data=callback)
                markup.add(btn)

            return Keyboards._add_menu(markup)
        
        @staticmethod
        def choose_subsection(article_section: ArticlesSection):
            subsections = article_section.subsections.all()
            markup = InlineKeyboardMarkup()

            for subsection in subsections:
                callback = Keyboards.build_callback_data(CallbackData.ARTICLES_SUBSECTION, {CallbackData.ARTICLES_SUBSECTION_ID: subsection.id})
                btn = InlineKeyboardButton(text=subsection.title, callback_data=callback)
                markup.add(btn)

            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.ARTICLES))
        
        @staticmethod
        def choose_article(article_subsection: ArticlesSubsection):
            articles = article_subsection.articles.all()
            markup = InlineKeyboardMarkup()

            for article in articles:
                title = parse_telegraph_title(article.link)
                btn = InlineKeyboardButton(text=title, url=article.link)
                markup.add(btn)

            return Keyboards._add_menu(Keyboards._add_back(markup, Keyboards.build_callback_data(CallbackData.ARTICLES_SECTION, {CallbackData.ARTICLES_SECTION_ID: article_subsection.section.id})))
        
    class Quizzes:
        @staticmethod
        def choose_topic():
            topics = QuizTopic.objects.all()
            markup = InlineKeyboardMarkup()

            for topic in topics:
                callback = Keyboards.build_callback_data(CallbackData.QUIZZES_TOPIC, {CallbackData.QUIZZES_TOPIC_ID: topic.id})
                btn = InlineKeyboardButton(text=topic.title, callback_data=callback)
                markup.add(btn)

            return Keyboards._add_menu(markup)

        @staticmethod
        def choose_level(quiz_topic: QuizTopic) -> InlineKeyboardMarkup:
            levels = QuizLevel.objects.filter(quizzes_by_level__topic=quiz_topic).distinct()
            markup = InlineKeyboardMarkup()

            for level in levels:
                callback = Keyboards.build_callback_data(
                    CallbackData.QUIZZES_LEVEL,
                    {
                        CallbackData.QUIZZES_LEVEL_ID: level.id,
                        CallbackData.QUIZZES_TOPIC_ID: quiz_topic.id
                    }
                )
                btn = InlineKeyboardButton(text=level.title, callback_data=callback)
                markup.add(btn)

            return Keyboards._add_menu(Keyboards._add_back(markup, CallbackData.QUIZZES))

        @staticmethod
        def choose_quiz(quiz_topic: QuizTopic, quiz_level: QuizLevel) -> InlineKeyboardMarkup:
            quizzes = Quiz.objects.filter(topic=quiz_topic, level=quiz_level)
            markup = InlineKeyboardMarkup()

            for quiz in quizzes:
                callback = Keyboards.build_callback_data(
                    CallbackData.QUIZZES_QUIZ,
                    { CallbackData.QUIZZES_QUIZ_ID: quiz.id }
                )
                btn = InlineKeyboardButton(text=quiz.title or f"Тест #{quiz.id}", callback_data=callback)
                markup.add(btn)

            back_cb = Keyboards.build_callback_data(
                CallbackData.QUIZZES_TOPIC,
                {
                    CallbackData.QUIZZES_TOPIC_ID: quiz_topic.id
                }
            )
            return Keyboards._add_menu(Keyboards._add_back(markup, back_cb))

        @staticmethod
        def _add_back_to_choose_quiz_delete_session(markup: InlineKeyboardMarkup, quiz_topic: QuizTopic, quiz_level: QuizLevel, session: UserQuizSession) -> InlineKeyboardMarkup:
            back_cb = Keyboards.build_callback_data(
            CallbackData.QUIZZES_LEVEL, 
            {
                CallbackData.QUIZZES_LEVEL_ID: quiz_level.id,
                CallbackData.QUIZZES_TOPIC_ID: quiz_topic.id,
                CallbackData.QUIZZES_QUIZ_SESSION_DELETE_ID: session.id, 
            })
            btn = InlineKeyboardButton(text=ButtonNames.QUIZZES_BACK_TO_CHOISE_QUIZ, callback_data=back_cb)
            markup.add(btn)
            return markup
        
        @staticmethod
        def _add_menu_delete_session(markup: InlineKeyboardMarkup, session: UserQuizSession) -> InlineKeyboardMarkup:
            menu_cb = Keyboards.build_callback_data(
            CallbackData.MENU, 
            {
                CallbackData.QUIZZES_QUIZ_SESSION_DELETE_ID: session.id, 
            })
            menu_btn = InlineKeyboardButton(text=ButtonNames.QUIZZES_BACK_TO_CHOISE_QUIZ, callback_data=menu_cb)
            markup.add(menu_btn)
            return markup
    

        @staticmethod
        def question(question: Question, session: UserQuizSession) -> InlineKeyboardMarkup:
            markup = InlineKeyboardMarkup()

            choices = Choice.objects.filter(question=question).order_by("order")
            if choices.exists():
                for choice in choices:
                    callback = Keyboards.build_callback_data(
                        CallbackData.QUIZZES_QUIZ_QUESTION_CHOISE, 
                        {
                            CallbackData.QUIZZES_QUIZ_QUESTION_CHOISE_ID: choice.id,
                            CallbackData.QUIZZES_QUIZ_SESSION_ID: session.id,
                        })
                    btn = InlineKeyboardButton(text=choice.text, callback_data=callback)
                    markup.add(btn)
                    
            return Keyboards.Quizzes._add_menu_delete_session(
                Keyboards.Quizzes._add_back_to_choose_quiz_delete_session(
                    markup,question.quiz.level,
                    question.quiz.topic,
                    session
                ), 
                session
            )
        
        @staticmethod
        def end(session: UserQuizSession) -> InlineKeyboardMarkup:
            markup = InlineKeyboardMarkup()
            back_cb = Keyboards.build_callback_data(
                CallbackData.QUIZZES_LEVEL, 
                { 
                    CallbackData.QUIZZES_LEVEL_ID: session.quiz.level.id,
                    CallbackData.QUIZZES_TOPIC_ID: session.quiz.topic.id
                })
            btn = InlineKeyboardButton(text=ButtonNames.QUIZZES_BACK_TO_CHOISE_QUIZ, callback_data=back_cb)
            markup.add(btn)
            return Keyboards._add_menu(markup)