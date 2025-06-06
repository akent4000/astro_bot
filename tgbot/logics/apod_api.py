# tgbot/logics/apod_api.py

import requests
from datetime import datetime
from io import BytesIO
from django.db import transaction

from tgbot.models import ApodApiKey, ApodFile
from tgbot.logics.constants import Constants

from pathlib import Path
from loguru import logger

# Убедимся, что папка logs существует
Path("logs").mkdir(parents=True, exist_ok=True)

# Лог-файл будет называться так же, как модуль, например apod_api.py → logs/apod_api.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")


class APODClientError(Exception):
    """Исключение для ошибок при работе с APODClient."""
    pass


class APODClient:
    """
    Клиент для получения данных NASA APOD и работы с моделью ApodFile.
    """

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key (str, optional): API-ключ NASA. Если не передан, берётся из модели ApodApiKey.
        """
        if api_key:
            self.api_key = api_key
            logger.debug("APODClient: API key передан явно.")
        else:
            self.api_key = ApodApiKey.get_solo().api_key
            logger.debug("APODClient: API key взят из модели ApodApiKey.")

        if not self.api_key:
            logger.error("APODClient: API key отсутствует.")
            raise APODClientError(
                "NASA API key not provided. Set it via parameter or environment variable NASA_API_KEY."
            )
        logger.info("APODClient инициализирован с API key.")


    def get_or_update_today(self) -> ApodFile:
        """
        Получает объект ApodFile для сегодняшней даты (UTC). 
        Если его нет, создаёт и запрашивает API для заполнения title/explanation.
        Если модель уже есть и в ней уже есть telegram_media_id, возвращает сразу.
        Иначе обновляет title/explanation из API.
        Возвращает ApodFile.date как объект date.
        """
        # Формируем чисто Python-объект datetime.date
        today_date = datetime.utcnow().date()
        logger.debug(f"get_or_update_today: Работаем с датой {today_date.isoformat()}")

        with transaction.atomic():
            apod_obj, created = ApodFile.objects.get_or_create(date=today_date)
            if created:
                logger.info(f"get_or_update_today: Создан новый ApodFile для {today_date}")
            else:
                logger.debug(f"get_or_update_today: Найден ApodFile для {today_date}")

            # Если уже есть media_id, нет смысла перезапрашивать API
            if not created and apod_obj.telegram_media_id:
                logger.info(f"get_or_update_today: У ApodFile для {today_date} уже есть telegram_media_id={apod_obj.telegram_media_id}")
                return apod_obj

            # Иначе запрашиваем метаданные из NASA API
            date_str = today_date.strftime("%Y-%m-%d")
            try:
                data = self._fetch_apod_data_for_date(date_str)
                logger.debug(f"get_or_update_today: Получены данные из API для {date_str}: {data}")
            except APODClientError as e:
                logger.error(f"get_or_update_today: Ошибка запроса к API для {date_str}: {e}")
                raise

            apod_obj.title = data.get("title", "")
            apod_obj.explanation = data.get("explanation", "")
            apod_obj.save(update_fields=["title", "explanation"])
            logger.info(f"get_or_update_today: Обновлены title/explanation для ApodFile {today_date}")

            return apod_obj


    def fetch_image_bytes(self, date_str: str) -> BytesIO:
        """
        Скачивает изображение APOD для указанной даты (string 'YYYY-MM-DD') в память.
        """
        logger.debug(f"fetch_image_bytes: Запрос API для даты {date_str}")
        data = self._fetch_apod_data_for_date(date_str)

        if data.get("media_type") != "image":
            msg = f"APOD for {date_str} is not an image (media_type={data.get('media_type')})"
            logger.error(f"fetch_image_bytes: {msg}")
            raise APODClientError(msg)

        image_url = data.get("hdurl") or data.get("url")
        logger.info(f"fetch_image_bytes: Скачиваем изображение с {image_url}")
        try:
            img_resp = requests.get(image_url, stream=True, timeout=10)
            img_resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"fetch_image_bytes: Ошибка при скачивании: {e}")
            raise APODClientError(f"Failed to download APOD image: {e}")

        buffer = BytesIO(img_resp.content)
        logger.info(f"fetch_image_bytes: Изображение загружено, размер {len(img_resp.content)} байт")
        return buffer


    def _fetch_apod_data_for_date(self, date_str: str) -> dict:
        """
        Запрос к NASA APOD API за данными (json) для даты date_str.
        """
        endpoint = Constants.NASA_APOD_ENDPOINT
        params = {"api_key": self.api_key, "date": date_str}
        logger.debug(f"_fetch_apod_data_for_date: GET {endpoint}?{params}")

        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            logger.info(f"_fetch_apod_data_for_date: Успешный ответ {resp.status_code} для {date_str}")
        except requests.RequestException as e:
            logger.error(f"_fetch_apod_data_for_date: Сетевая ошибка: {e}")
            raise APODClientError(f"Network error while fetching APOD: {e}")

        try:
            data = resp.json()
            logger.debug(f"_fetch_apod_data_for_date: JSON payload: {data}")
        except ValueError:
            logger.error(f"_fetch_apod_data_for_date: Не удалось распарсить JSON для {date_str}")
            raise APODClientError("Failed to parse JSON from NASA APOD API.")

        if "media_type" not in data or "url" not in data:
            logger.error(f"_fetch_apod_data_for_date: Ожидаемые поля отсутствуют в ответе: {data}")
            raise APODClientError("Unexpected APOD response structure.")

        return data
