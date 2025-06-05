import datetime
import math

def moon_phase(date: datetime.datetime | datetime.date):
    if isinstance(date, datetime.datetime):
        year = date.year
        month = date.month
        day = date.day
    elif isinstance(date, datetime.date):
        year = date.year
        month = date.month
        day = date.day
    else:
        raise TypeError("Аргумент date должен быть datetime.date или datetime.datetime")

    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jd = day + ((153 * m + 2) // 5) + 365 * y + (y // 4) - (y // 100) + (y // 400) - 32045

    JD_REF = 2451550.1

    SYNODIC_MONTH = 29.53058867 

    days_since_new = jd + 0.5 - JD_REF
    new_moons = days_since_new / SYNODIC_MONTH
    frac = new_moons - math.floor(new_moons)
    age = frac * SYNODIC_MONTH 

    phase_names = [
        "Новолуние",         # 1
        "Растущий серп",     # 2
        "Первая четверть",   # 3
        "Рассветная четверть",# 4
        "Полнолуние",        # 5
        "Убывающий серп",    # 6
        "Последняя четверть",# 7
        "Вечерняя четверть", # 8
    ]
    phase_emojis = [
        "🌑",  # Новолуние
        "🌒",  # Растущий серп
        "🌓",  # Первая четверть
        "🌔",  # Рассветная четверть
        "🌕",  # Полнолуние
        "🌖",  # Убывающий серп
        "🌗",  # Последняя четверть
        "🌘",  # Вечерняя четверть
    ]

    if age < 1.84566:
        idx = 0
    elif age < 5.53699:
        idx = 1
    elif age < 9.22831:
        idx = 2
    elif age < 12.91963:
        idx = 3
    elif age < 16.61096:
        idx = 4
    elif age < 20.30228:
        idx = 5
    elif age < 23.99361:
        idx = 6
    elif age < 27.68493:
        idx = 7
    else:
        idx = 0 

    phase_number = idx + 1
    phase_name = phase_names[idx]
    phase_emoji = phase_emojis[idx]

    return f"{phase_number}. {phase_emoji} {phase_name}"