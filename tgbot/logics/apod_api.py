# tgbot/logics/apod_api.py

import os
import requests
from datetime import datetime
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import transaction

from tgbot.models import ApodApiKey, ApodFile

from tgbot.logics.constants import Constants

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
            api_key (str, optional): API-ключ NASA. Если не передан, попытается взять из env NASA_API_KEY.
        """
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = ApodApiKey.get_solo().api_key
        if not self.api_key:
            raise APODClientError(
                "NASA API key not provided. Set it via parameter or environment variable NASA_API_KEY."
            )

    def get_or_update_today(self) -> ApodFile:
        """
        Получает объект ApodFile для сегодняшней даты. Если его нет, запрашивает API и сохраняет метаданные.
        Возвращает:
            ApodFile: экземпляр модели, в котором заполняются date, title, explanation и (возможно) telegram_media_id.
        """
        today_str = datetime.utcnow().strftime("%Y-%m-%d")

        # atomic, чтобы избежать двух одновременных запросов к API для одной даты
        with transaction.atomic():
            apod_obj, created = ApodFile.objects.get_or_create(date=today_str)

            if not created and apod_obj.telegram_media_id:
                # Уже есть запись с media_id → ничего не меняем
                return apod_obj

            # Нужно запросить из API и обновить метаданные
            data = self._fetch_apod_data_for_date(today_str)

            # Обновляем title и explanation
            apod_obj.title = data.get("title", "")
            apod_obj.explanation = data.get("explanation", "")
            apod_obj.save(update_fields=["title", "explanation"])

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
        data = self._fetch_apod_data_for_date(date_str)

        if data.get("media_type") != "image":
            raise APODClientError(f"APOD for {date_str} is not an image.")

        image_url = data.get("hdurl") or data.get("url")
        try:
            img_resp = requests.get(image_url, stream=True, timeout=10)
            img_resp.raise_for_status()
        except requests.RequestException as e:
            raise APODClientError(f"Failed to download APOD image: {e}")

        buffer = BytesIO(img_resp.content)
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
        params = {"api_key": self.api_key, "date": date_str}
        try:
            resp = requests.get(Constants.NASA_APOD_ENDPOINT, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise APODClientError(f"Network error while fetching APOD: {e}")

        try:
            data = resp.json()
        except ValueError:
            raise APODClientError("Failed to parse JSON from NASA APOD API.")

        if "media_type" not in data or "url" not in data:
            raise APODClientError("Unexpected APOD response structure.")

        return data
