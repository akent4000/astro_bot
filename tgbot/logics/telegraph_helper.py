import re
import requests


def parse_telegraph_title(url: str) -> str | None:
    """
    Запрашивает страницу telegra.ph и извлекает текст внутри тега <title>.
    Убирает суффикс « | Telegra.ph » или аналогичный.
    Возвращает None, если что-то пошло не так.
    """
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        html = resp.text
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        raw_title = match.group(1).strip()
        # Убираем « | Telegra.ph » или « – Telegra.ph » и всё, что после
        cleaned = re.sub(r"\s*[|–-]\s*Telegra\.ph.*$", "", raw_title).strip()
        return cleaned or None
    except Exception:
        return None