import json
import logging
import os
import time
import shutil

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir="data", max_age_days=7):
        self.cache_dir = cache_dir
        self.max_age_seconds = max_age_days * 24 * 60 * 60
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_filepath(self, key):
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key):
        filepath = self._get_filepath(key)
        if not os.path.exists(filepath):
            return None

        try:
            file_age = time.time() - os.path.getmtime(filepath)
            if file_age > self.max_age_seconds:
                logger.info(f"Cache expired for {key} (Age: {file_age/86400:.1f} days)")
                return None

            with open(filepath, "r") as f:
                data = json.load(f)
                # Inline validation check
                if data is None or (isinstance(data, (list, dict)) and not data):
                    logger.warning(f"Invalid cached data found for {key}, ignoring.")
                    return None
                logger.info(f"Using cached data for {key}")
                return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load cache from {filepath}: {e}")
            return None

    def set(self, key, data):
        # Inline validation check
        if data is None or (isinstance(data, (list, dict)) and not data):
            logger.warning(f"Skipping cache for {key} due to invalid data (None or empty).")
            return

        filepath = self._get_filepath(key)
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached data for {key}")
        except OSError as e:
            logger.error(f"Failed to write cache to {filepath}: {e}")

    def clear(self):
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
