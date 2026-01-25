import unittest
import asyncio
import json
import os
import time
import datetime
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
from main import process_service_item, get_cached_data

# Dummy data
MOCK_ITEM = {
    "csp_a_service_name": "ServiceA",
    "csp_b_service_name": "ServiceB",
    "csp_a_url": "http://a",
    "csp_b_url": "http://b"
}
SERVICE_PAIR_ID = "ServiceA_vs_ServiceB"

class TestCachingBehavior(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.tech_analyst = MagicMock()
        self.tech_analyst.perform_analysis = AsyncMock(return_value={"tech": "data"})

        self.pricing_analyst = MagicMock()
        self.pricing_analyst.perform_analysis = AsyncMock(return_value={"pricing": "data"})

        self.synthesizer = MagicMock()
        self.synthesizer.synthesize = AsyncMock(return_value={"result": "data"})

        self.semaphore = asyncio.Semaphore(1)

    async def test_get_cached_data_fresh(self):
        """Test that fresh data is loaded."""
        # Create a dummy file content
        content = json.dumps({"data": "cached"})

        # Mock file existence and open
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=time.time()), \
             patch("builtins.open", mock_open(read_data=content)):

            result = get_cached_data("dummy_path.json", max_age_days=7)
            self.assertEqual(result, {"data": "cached"})

    async def test_get_cached_data_stale(self):
        """Test that stale data is ignored."""
        # 8 days ago
        old_time = time.time() - (8 * 24 * 3600)

        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=old_time):

            result = get_cached_data("dummy_path.json", max_age_days=7)
            self.assertIsNone(result)

    async def test_get_cached_data_corrupt(self):
        """Test that corrupt data is ignored."""
        with patch("os.path.exists", return_value=True), \
             patch("os.path.getmtime", return_value=time.time()), \
             patch("builtins.open", mock_open(read_data="{invalid json")):

            result = get_cached_data("dummy_path.json", max_age_days=7)
            self.assertIsNone(result)

    async def test_process_service_item_fresh_cache(self):
        """
        Optimization Verification:
        If files exist and are fresh, analysts should NOT be called.
        """
        tech_content = json.dumps({"tech": "cached"})
        pricing_content = json.dumps({"pricing": "cached"})
        result_content = json.dumps({"result": "cached"})

        def side_effect(filepath, mode="r"):
            if "technical" in filepath:
                return mock_open(read_data=tech_content).return_value
            if "pricing" in filepath:
                return mock_open(read_data=pricing_content).return_value
            if "result" in filepath:
                return mock_open(read_data=result_content).return_value
            return mock_open().return_value

        with patch("main.get_cached_data") as mock_get_cache:
            # Setup: get_cached_data returns valid data
            mock_get_cache.side_effect = [
                {"tech": "cached"},    # 1st call: technical
                {"pricing": "cached"}, # 2nd call: pricing
                {"result": "cached"}   # 3rd call: synthesis
            ]

            await process_service_item(
                MOCK_ITEM,
                self.tech_analyst,
                self.pricing_analyst,
                self.synthesizer,
                "CSP_A",
                "CSP_B",
                self.semaphore
            )

            # ASSERTION: Calls should be SKIPPED
            self.tech_analyst.perform_analysis.assert_not_called()
            self.pricing_analyst.perform_analysis.assert_not_called()
            self.synthesizer.synthesize.assert_not_called()

    async def test_process_service_item_no_cache(self):
        """
        Verify fallback:
        If cache is missing/stale (get_cached_data returns None), analysts ARE called.
        """
        with patch("main.get_cached_data", return_value=None), \
             patch("builtins.open", mock_open()), \
             patch("json.dump"):

            await process_service_item(
                MOCK_ITEM,
                self.tech_analyst,
                self.pricing_analyst,
                self.synthesizer,
                "CSP_A",
                "CSP_B",
                self.semaphore
            )

            self.tech_analyst.perform_analysis.assert_called_once()
            self.pricing_analyst.perform_analysis.assert_called_once()
            self.synthesizer.synthesize.assert_called_once()

if __name__ == "__main__":
    unittest.main()
