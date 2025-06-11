import requests
from datetime import datetime, timedelta, timezone
from io import BytesIO
from django.db import transaction
from zoneinfo import ZoneInfo

from tgbot.models import ApodApiKey, ApodFile
from tgbot.logics.constants import Constants

from pathlib import Path
from loguru import logger

# Ensure logs directory exists
Path("logs").mkdir(parents=True, exist_ok=True)

# Log file named after module, e.g. apod_api.py → logs/apod_api.log
log_filename = Path("logs") / f"{Path(__file__).stem}.log"
logger.add(str(log_filename), rotation="10 MB", level="DEBUG")


class APODClientError(Exception):
    """Exception for APODClient errors."""
    pass


class APODClient:
    """
    Client for fetching NASA APOD data and managing ApodFile entries.

    Determines the correct APOD date based on UTC server time and NASA's ET publication at midnight Eastern Time.
    If the current time (converted to America/New_York) is before midnight ET, it fetches the previous day's APOD.
    """

    ET_TZ = ZoneInfo("America/New_York")
    UTC_TZ = timezone.utc

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key (str, optional): NASA API key. If not provided, taken from ApodApiKey singleton.
        """
        if api_key:
            self.api_key = api_key
            logger.debug("APODClient: API key provided explicitly.")
        else:
            self.api_key = ApodApiKey.get_solo().api_key
            logger.debug("APODClient: API key loaded from ApodApiKey model.")

        if not self.api_key:
            logger.error("APODClient: API key is missing.")
            raise APODClientError(
                "NASA API key not provided. Set it via parameter or environment variable NASA_API_KEY."
            )
        logger.info("APODClient initialized with API key.")

    def get_or_update_today(self) -> ApodFile:
        """
        Retrieves or updates the ApodFile for the current APOD date based on UTC server time.
        Converts current UTC time to America/New_York to decide if midnight ET has passed.
        Returns:
            ApodFile instance with title and explanation populated. Does not fetch media bytes.
        """
        # Current UTC time
        now_utc = datetime.now(self.UTC_TZ)
        # Convert to Eastern Time
        now_et = now_utc.astimezone(self.ET_TZ)
        # Today's date in ET
        et_date = now_et.date()
        # Midnight ET today
        et_midnight = now_et.replace(hour=0, minute=0, second=0, microsecond=0)

        # Determine target date: if before midnight ET, use previous day
        if now_et < et_midnight:
            target_date = et_date - timedelta(days=1)
            logger.debug(
                f"get_or_update_today: ET time {now_et.isoformat()} before midnight ET, using previous date {target_date}"
            )
        else:
            target_date = et_date
            logger.debug(
                f"get_or_update_today: ET time {now_et.isoformat()} after midnight ET, using date {target_date}"
            )

        date_str = target_date.isoformat()
        with transaction.atomic():
            apod_obj, created = ApodFile.objects.get_or_create(date=target_date)
            if created:
                logger.info(f"get_or_update_today: Created new ApodFile for {date_str}")
            else:
                logger.debug(f"get_or_update_today: Found existing ApodFile for {date_str}")

            # If media already uploaded to Telegram, skip metadata update
            if not created and apod_obj.telegram_media_id:
                logger.info(
                    f"get_or_update_today: ApodFile for {date_str} already has telegram_media_id={apod_obj.telegram_media_id}"
                )
                return apod_obj

            # Fetch metadata from NASA APOD API
            try:
                data = self._fetch_apod_data_for_date(date_str)
                logger.debug(f"get_or_update_today: Fetched data for {date_str}: {data}")
            except APODClientError as e:
                logger.error(f"get_or_update_today: Error fetching API data for {date_str}: {e}")
                raise

            # Update title and explanation
            apod_obj.title = data.get("title", "")
            apod_obj.explanation = data.get("explanation", "")
            apod_obj.save(update_fields=["title", "explanation"])
            logger.info(f"get_or_update_today: Updated title/explanation for ApodFile {date_str}")

            return apod_obj

    def fetch_image_bytes(self, date_str: str) -> BytesIO:
        """
        Downloads the APOD image for a given date 'YYYY-MM-DD'.
        On HTTP 404 when fetching the image, falls back to the previous day's image.
        Raises APODClientError for other failures or non-image media types.
        """
        logger.debug(f"fetch_image_bytes: Requesting API data for date {date_str}")
        data = self._fetch_apod_data_for_date(date_str)

        if data.get("media_type") != "image":
            msg = f"APOD for {date_str} is not an image (media_type={data.get('media_type')})"
            logger.error(f"fetch_image_bytes: {msg}")
            raise APODClientError(msg)

        image_url = data.get("hdurl") or data.get("url")
        logger.info(f"fetch_image_bytes: Downloading image from {image_url}")
        try:
            img_resp = requests.get(image_url, stream=True, timeout=10)
            # Fallback on 404: try previous date
            if img_resp.status_code == 404:
                logger.warning(
                    f"fetch_image_bytes: Image for {date_str} returned 404, fetching previous day"
                )
                prev_date = datetime.fromisoformat(date_str).date() - timedelta(days=1)
                return self.fetch_image_bytes(prev_date.isoformat())
            img_resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"fetch_image_bytes: Download error: {e}")
            raise APODClientError(f"Failed to download APOD image: {e}")

        buffer = BytesIO(img_resp.content)
        logger.info(f"fetch_image_bytes: Image loaded, size {len(img_resp.content)} bytes")
        return buffer

    def _fetch_apod_data_for_date(self, date_str: str) -> dict:
        """
        Internal: requests metadata JSON from NASA APOD API for given date.
        """
        endpoint = Constants.NASA_APOD_ENDPOINT
        params = {"api_key": self.api_key, "date": date_str}
        logger.debug(f"_fetch_apod_data_for_date: GET {endpoint}?{params}")

        try:
            resp = requests.get(endpoint, params=params, timeout=10)
            resp.raise_for_status()
            logger.info(f"_fetch_apod_data_for_date: Successful response {resp.status_code} for {date_str}")
        except requests.RequestException as e:
            logger.error(f"_fetch_apod_data_for_date: Network error: {e}")
            raise APODClientError(f"Network error while fetching APOD: {e}")

        try:
            data = resp.json()
            logger.debug(f"_fetch_apod_data_for_date: JSON payload: {data}")
        except ValueError:
            logger.error(f"_fetch_apod_data_for_date: Failed to parse JSON for {date_str}")
            raise APODClientError("Failed to parse JSON from NASA APOD API.")

        if "media_type" not in data or "url" not in data:
            logger.error(f"_fetch_apod_data_for_date: Missing expected fields in response: {data}")
            raise APODClientError("Unexpected APOD response structure.")

        return data
