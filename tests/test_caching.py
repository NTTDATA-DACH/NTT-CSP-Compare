import unittest
import asyncio
import json
import os
import time
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

from pipeline.cache import CacheManager
from main import process_service_item

# Dummy data
MOCK_ITEM = {
    "csp_a_service_name": "ServiceA",
    "csp_b_service_name": "ServiceB",
    "csp_a_url": "http://a",
    "csp_b_url": "http://b"
}
SERVICE_PAIR_ID = "ServiceA_vs_ServiceB"

class TestCacheManager(unittest.TestCase):

    def test_get_fresh_data(self):
        """Test that fresh data is loaded correctly."""
        cache = CacheManager()
        content = json.dumps({"data": "cached"})

        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=time.time()), \
             patch("builtins.open", mock_open(read_data=content)):

            result = cache.get("some_key")
            self.assertEqual(result, {"data": "cached"})

    def test_get_stale_data(self):
        """Test that stale data is ignored."""
        cache = CacheManager(max_age_days=7)
        old_time = time.time() - (8 * 24 * 3600) # 8 days ago

        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=old_time):

            result = cache.get("some_key")
            self.assertIsNone(result)

    def test_get_corrupt_data(self):
        """Test that corrupt JSON data is handled."""
        cache = CacheManager()

        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=time.time()), \
             patch("builtins.open", mock_open(read_data="{invalid json")):

            result = cache.get("some_key")
            self.assertIsNone(result)

    def test_get_invalid_data(self):
        """Test that invalid (e.g., empty) data is handled."""
        cache = CacheManager()

        # Test with empty dict
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=time.time()), \
             patch("builtins.open", mock_open(read_data="{}")):

            result = cache.get("some_key")
            self.assertIsNone(result)

    def test_set_valid_data(self):
        """Test setting valid data to cache."""
        cache = CacheManager()

        with patch("builtins.open", mock_open()) as mocked_file, \
             patch("json.dump") as mock_json_dump:

            cache.set("my_key", {"data": "is_good"})
            mocked_file.assert_called_once_with(os.path.join("data", "my_key.json"), "w")
            mock_json_dump.assert_called_once()

    def test_set_invalid_data(self):
        """Test that invalid data is not written to cache."""
        cache = CacheManager()

        with patch("builtins.open", mock_open()) as mocked_file:
            # Test with None, empty dict, empty list
            cache.set("my_key", None)
            cache.set("my_key", {})
            cache.set("my_key", [])
            mocked_file.assert_not_called()

class TestPipelineCachingBehavior(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.tech_analyst = MagicMock()
        self.tech_analyst.perform_analysis = AsyncMock(return_value={"tech": "data"})

        self.pricing_analyst = MagicMock()
        self.pricing_analyst.perform_analysis = AsyncMock(return_value={"pricing": "data"})

        self.synthesizer = MagicMock()
        self.synthesizer.synthesize = AsyncMock(return_value={"synthesis": "data"})

        self.semaphore = asyncio.Semaphore(1)

    async def test_process_service_item_uses_cache(self):
        """
        Optimization Verification:
        If cache is fresh, analysts should NOT be called.
        """
        # Setup mock CacheManager
        mock_cache = MagicMock(spec=CacheManager)
        mock_cache.get.side_effect = [
            {"tech": "cached"},
            {"pricing": "cached"},
            {"result": "cached"}
        ]

        await process_service_item(
            MOCK_ITEM,
            self.tech_analyst,
            self.pricing_analyst,
            self.synthesizer,
            "CSP_A",
            "CSP_B",
            mock_cache,
            self.semaphore
        )

        # ASSERTIONS
        # Analysts should not be called
        self.tech_analyst.perform_analysis.assert_not_called()
        self.pricing_analyst.perform_analysis.assert_not_called()
        self.synthesizer.synthesize.assert_not_called()
        # Cache should not be written to
        mock_cache.set.assert_not_called()

    async def test_process_service_item_no_cache(self):
        """
        Verify fallback:
        If cache is missing, analysts ARE called and results ARE cached.
        """
        # Setup mock CacheManager to return nothing
        mock_cache = MagicMock(spec=CacheManager)
        mock_cache.get.return_value = None

        await process_service_item(
            MOCK_ITEM,
            self.tech_analyst,
            self.pricing_analyst,
            self.synthesizer,
            "CSP_A",
            "CSP_B",
            mock_cache,
            self.semaphore
        )

        # ASSERTIONS
        # Analysts should be called
        self.tech_analyst.perform_analysis.assert_called_once()
        self.pricing_analyst.perform_analysis.assert_called_once()
        self.synthesizer.synthesize.assert_called_once()

        # Cache should be written to 3 times (tech, pricing, synth)
        self.assertEqual(mock_cache.set.call_count, 3)

if __name__ == "__main__":
    unittest.main()
