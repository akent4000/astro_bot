class CallbackData:
    # Общий ключ для ID
    ID = "i"

    # Основные действия
    BACK = "b"
    MENU = "m"
    MENU_FORCED_DELETE = "mfd"

    # Параметры времени
    TODAY = "t"
    ENTER_DATE = "d"
    ENTER_TIME = "ti"

    # MoonCalc
    MOON_CALC = "mc"
    MOON_CALC_TODAY = f"{MOON_CALC}_{TODAY}"          # "mc_t"
    MOON_CALC_ENTER_DATE = f"{MOON_CALC}_{ENTER_DATE}" # "mc_d"

    # IntFacts
    INT_FACTS = "if"
    INT_FACTS_TODAY = f"{INT_FACTS}_{TODAY}"            # "if_t"
    INT_FACTS_SUB = f"{INT_FACTS}_s"                    # "if_s"
    INT_FACTS_UNSUB = f"{INT_FACTS}_u"                  # "if_u"
    INT_FACTS_DEFAULT_TIME = f"{INT_FACTS}_dt"          # "if_dt"
    INT_FACTS_ENTER_TIME = f"{INT_FACTS}_{ENTER_TIME}"  # "if_ti"

    # APOD
    APOD = "ap"

    # Articles
    ARTICLES = "ar"
    ARTICLES_SECTION = f"{ARTICLES}_sc"                     # "ar_sc"
    ARTICLES_SECTION_ID = f"{ARTICLES_SECTION}_{ID}"        # "ar_sc_i"
    ARTICLES_SUBSECTION = f"{ARTICLES}_ss"                  # "ar_ss"
    ARTICLES_SUBSECTION_ID = f"{ARTICLES_SUBSECTION}_{ID}"  # "ar_ss_i"
    ARTICLES_ARTICLE = f"{ARTICLES}_a"                      # "ar_a"
    ARTICLES_ARTICLE_ID = f"{ARTICLES_ARTICLE}_{ID}"        # "ar_a_i"

    # Quizzes
    QUIZZES = "qz"
    QUIZZES_TOPIC = f"{QUIZZES}_t"                      # "qz_t"
    QUIZZES_TOPIC_ID = f"{QUIZZES_TOPIC}_{ID}"          # "qz_t_i"
    QUIZZES_LEVEL = f"{QUIZZES}_l"                      # "qz_l"
    QUIZZES_LEVEL_ID = f"{QUIZZES_LEVEL}_{ID}"          # "qz_l_i"
    QUIZZES_QUIZ = f"{QUIZZES}_q"                       # "qz_q"
    QUIZZES_QUIZ_ID = f"{QUIZZES_QUIZ}_{ID}"            # "qz_q_i"


class Commands:
    START = "start"

class ButtonNames:
    BACK = "Назад"
    MENU = "Меню"

    TODAY = "Сегодня"
    ENTER_DATE = "Ввести дату"
    ENTER_TIME = "Ввести время"

    MOON_CALC = "Калькулятор фаз Луны"

    INT_FACTS = "Интересные факты"
    INT_FACTS_SUB = "Подписаться на ежедневную рассылку"
    INT_FACTS_UNSUB = "Отписаться от ежедневной рассылки"
    INT_FACTS_DEFAULT_TIME = "11:00"

    APOD = "Фото дня"

    ARTICLES = "Статьи"

    QUIZZES = "Квизы"

    GLOSSARY = "Глоссарий"

class Urls:
    pass
class Constants:
    NASA_APOD_ENDPOINT = "https://api.nasa.gov/planetary/apod"
    ZONE_INFO = "Europe/Moscow"

class Messages:
    MENU_MESSAGE = "Меню"
    
    MOON_CALC = "Калькулятор фаз Луны"
    MOON_CALC_MSG = "{date}\n{moon_phase}"
    MOON_CALC_TODAY = f"Сегодня {MOON_CALC_MSG}"
    MOON_CALC_ENTER_DATE = "Введите дату в формате дд.мм.гггг, например: 05.06.2025"
    MOON_CALC_ENTER_DATE_INCORRECT = "Неверный формат даты. Введите дату в формате дд.мм.гггг, например: 05.06.2025"

    INT_FACTS = "Интересные факты"
    INT_FACTS_FACT = "Интересный факт {id}"
    INT_FACTS_FACT_TODAY_NOT_FOUND = "К сожалению, на сегодня интересный факт отсутствует"

    ARTICLES_SECTION = "Выберите раздел"
    ARTICLES_SUBSECTION = "Выберите подраздел"
    ARTICLES_ARTICLE = "Список статей по этой теме:"

    USER_BLOCKED = "❌ Вы заблокированы и не можете пользоваться ботом."
    USER_NOT_FOUND_ERROR = "Ошибка: пользователь не найден."
    MISSING_PARAMETERS_ERROR = "Ошибка: отсутствуют параметры."
    INCORRECT_VALUE_ERROR = "Ошибка: неверное значение для {key}."
    NOT_FOUND_ERROR = "{item} не найден."

class CommandsNames:
    START = "Старт бота и показ меню"