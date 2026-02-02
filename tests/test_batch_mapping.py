import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio
from pipeline.discovery import ServiceMapper

class TestBatchMapping(unittest.IsolatedAsyncioTestCase):

    @patch("builtins.open")
    @patch("pipeline.discovery.GeminiClient")
    async def test_map_services_batching(self, MockGeminiClient, mock_open):
        # Setup mocks for file reading
        prompt_config_mock = {
            "service_map_batch_prompt": {
                "system_instruction": "sys",
                "user_template": "user {services_a} {services_b}"
            },
            "service_list_prompt": {"system_instruction": "", "user_template": ""}
        }

        def open_side_effect(filename, mode):
            mock_f = MagicMock()
            if "prompt_config.json" in str(filename):
                mock_f.read.return_value = json.dumps(prompt_config_mock)
            else:
                mock_f.read.return_value = "{}"
            mock_f.__enter__.return_value = mock_f
            return mock_f

        mock_open.side_effect = open_side_effect

        # Create a mock client instance
        mock_client_instance = MockGeminiClient.return_value

        async def generate_content_side_effect(*args, **kwargs):
            return {
                "items": [{"mapped": "true"}]
            }

        mock_client_instance.generate_content = AsyncMock(side_effect=generate_content_side_effect)

        # Initialize Mapper
        with patch('pipeline.discovery.Config.TEST_MODE', False):
            mapper = ServiceMapper()

            # Create dummy services input (e.g. 25 services)
            # Batch size is 20. So 25 -> 2 batches (20, 5).
            services_a = [{"service_name": f"Service A {i}"} for i in range(25)]
            services_b = [{"service_name": f"Service B {i}"} for i in range(10)]

            csp_a = "CSP_A"
            csp_b = "CSP_B"

            # Execute
            result = await mapper.map_services(csp_a, csp_b, services_a, services_b)

            # Verification
            # 25 items, batch size 20 -> 2 batches.
            self.assertEqual(mock_client_instance.generate_content.call_count, 2)

            # The result should be the concatenation of the returns.
            # Our side effect returned 1 item per call. Total 2 items.
            self.assertEqual(len(result["items"]), 2)

            # Verify aggregation logic:
            self.assertEqual(result["items"], [{"mapped": "true"}, {"mapped": "true"}])

    @patch("builtins.open")
    @patch("pipeline.discovery.GeminiClient")
    async def test_map_services_batching_error_fallback(self, MockGeminiClient, mock_open):
        # Setup mocks for file reading (valid prompt config)
        prompt_config_mock = {
            "service_map_batch_prompt": {
                "system_instruction": "sys",
                "user_template": "user"
            },
            "service_list_prompt": {"system_instruction": "", "user_template": ""}
        }

        def open_side_effect(filename, mode):
            mock_f = MagicMock()
            if "prompt_config.json" in str(filename):
                mock_f.read.return_value = json.dumps(prompt_config_mock)
            else:
                mock_f.read.return_value = "{}"
            mock_f.__enter__.return_value = mock_f
            return mock_f

        mock_open.side_effect = open_side_effect

        # Mock generate_content to raise exception
        mock_client_instance = MockGeminiClient.return_value
        mock_client_instance.generate_content.side_effect = Exception("API Error")

        with patch('pipeline.discovery.Config.TEST_MODE', False):
            mapper = ServiceMapper()

            # Input: 5 services
            services_a = [{"service_name": f"Service A {i}", "domain": "Compute", "service_url": "url"} for i in range(5)]
            services_b = []

            result = await mapper.map_services("CSP_A", "CSP_B", services_a, services_b)

            # Should have 5 items (fallbacks)
            self.assertEqual(len(result["items"]), 5)
            self.assertEqual(result["items"][0]["csp_a_service_name"], "Service A 0")
            self.assertIsNone(result["items"][0]["csp_b_service_name"])

if __name__ == '__main__':
    unittest.main()
