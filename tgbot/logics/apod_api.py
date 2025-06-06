# tgbot/logics/apod_api.py

import os
import requests
from datetime import datetime
from io import BytesIO
from django.core.files.base import ContentFile
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
            api_key (str, optional): API-ключ NASA. Если не передан, попытается взять из модели ApodApiKey.
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
        Получает объект ApodFile для сегодняшней даты. Если его нет, запрашивает API и сохраняет метаданные.
        Возвращает:
            ApodFile: экземпляр модели, в котором заполняются date, title, explanation и (возможно) telegram_media_id.
        """
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        logger.debug(f"get_or_update_today: Начало для даты {today_str}")

        with transaction.atomic():
            apod_obj, created = ApodFile.objects.get_or_create(date=today_str)
            if created:
                logger.info(f"get_or_update_today: Создан новый объект ApodFile для даты {today_str}")
            else:
                logger.debug(f"get_or_update_today: Найден существующий объект ApodFile для даты {today_str}")

            if not created and apod_obj.telegram_media_id:
                logger.info(f"get_or_update_today: Объект для {today_str} уже имеет telegram_media_id={apod_obj.telegram_media_id}, возврат без изменений.")
                return apod_obj

            # Если создан или media_id отсутствует, запрашиваем данные из API
            try:
                data = self._fetch_apod_data_for_date(today_str)
                logger.debug(f"get_or_update_today: Получены данные из API для {today_str}: {data}")
            except APODClientError as e:
                logger.error(f"get_or_update_today: Ошибка при запросе API для {today_str}: {e}")
                raise

            # Обновляем поля title и explanation
            apod_obj.title = data.get("title", "")
            apod_obj.explanation = data.get("explanation", "")
            apod_obj.save(update_fields=["title", "explanation"])
            logger.info(f"get_or_update_today: Обновлены метаданные для ApodFile {today_str} (title, explanation).")
            return apod_obj


    def fetch_image_bytes(self, date_str: str) -> BytesIO:
        """
        Скачивает изображение APOD для указанной даты в оперативную память.
        Args:
            date_str (str): дата в формате 'YYYY-MM-DD'.
        Returns:
            BytesIO: байты изображения.
        Raises:
            APODClientError: если media_type != image или произошла сетевая ошибка.
        """
        logger.debug(f"fetch_image_bytes: Запрос данных APOD для даты {date_str}")
        data = self._fetch_apod_data_for_date(date_str)

        if data.get("media_type") != "image":
            msg = f"APOD for {date_str} is not an image (media_type={data.get('media_type')})"
            logger.error(f"fetch_image_bytes: {msg}")
            raise APODClientError(msg)

        image_url = data.get("hdurl") or data.get("url")
        logger.info(f"fetch_image_bytes: Скачивание изображения по URL: {image_url}")
        try:
            img_resp = requests.get(image_url, stream=True, timeout=10)
            img_resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"fetch_image_bytes: Ошибка при скачивании изображения: {e}")
            raise APODClientError(f"Failed to download APOD image: {e}")

        buffer = BytesIO(img_resp.content)
        logger.info(f"fetch_image_bytes: Успешно загружено изображение для {date_str}, размер {len(img_resp.content)} байт.")
        return buffer


    def _fetch_apod_data_for_date(self, date_str: str) -> dict:
        """
        Запрос к NASA APOD API для указанной даты.
        Args:
            date_str (str): дата 'YYYY-MM-DD'
        Returns:
            dict: ответ API.
        Raises:
            APODClientError: если статус != 200 или JSON некорректен.
        """
        endpoint = Constants.NASA_APOD_ENDPOINT
        params = {"api_key": self.api_key, "date": date_str}
        logger.debug(f"_fetch_apod_data_for_date: Запрос к {endpoint} с параметрами {params}")

        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            logger.info(f"_fetch_apod_data_for_date: Получен ответ {resp.status_code} от API для {date_str}")
        except requests.RequestException as e:
            logger.error(f"_fetch_apod_data_for_date: Сетевая ошибка при запросе API: {e}")
            raise APODClientError(f"Network error while fetching APOD: {e}")

        try:
            data = resp.json()
            logger.debug(f"_fetch_apod_data_for_date: JSON ответ: {data}")
        except ValueError:
            logger.error(f"_fetch_apod_data_for_date: Не удалось распарсить JSON из ответа API.")
            raise APODClientError("Failed to parse JSON from NASA APOD API.")

        if "media_type" not in data or "url" not in data:
            logger.error(f"_fetch_apod_data_for_date: В ответе отсутствуют обязательные поля: media_type или url.")
            raise APODClientError("Unexpected APOD response structure.")

        return data
