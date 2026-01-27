import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import json
from pipeline.gemini import GeminiClient
from google.genai import errors

class TestGeminiClientWithTestMode(unittest.IsolatedAsyncioTestCase):
    @patch('pipeline.gemini.Config.TEST_MODE', True)
    async def test_generate_content_success(self):
        client = GeminiClient()
        mock_response = MagicMock()
        mock_response.parsed = {"result": "success"}
        client.client.models.generate_content.return_value = mock_response

        result = await client.generate_content("model", "user", "system")
        self.assertEqual(result, {"result": "success"})
        client.client.models.generate_content.assert_called_once()

    @patch('pipeline.gemini.Config.TEST_MODE', True)
    async def test_generate_content_retry_on_api_error(self):
        client = GeminiClient()
        client.client.models.generate_content.side_effect = errors.APIError(500, {}, None)

        result = await client.generate_content("model", "user", "system")
        self.assertIsNone(result)
        self.assertEqual(client.client.models.generate_content.call_count, 3)

    @patch('pipeline.gemini.Config.TEST_MODE', True)
    async def test_generate_content_retry_on_value_error(self):
        client = GeminiClient()
        client.client.models.generate_content.side_effect = ValueError("Validation failed")

        result = await client.generate_content("model", "user", "system")
        self.assertIsNone(result)
        self.assertEqual(client.client.models.generate_content.call_count, 3)

    @patch('pipeline.gemini.Config.TEST_MODE', True)
    async def test_generate_content_retry_on_json_error(self):
        client = GeminiClient()
        client.client.models.generate_content.side_effect = json.JSONDecodeError("msg", "doc", 0)

        result = await client.generate_content("model", "user", "system")
        self.assertIsNone(result)
        self.assertEqual(client.client.models.generate_content.call_count, 3)

    @patch('pipeline.gemini.Config.TEST_MODE', True)
    async def test_generate_content_success_after_retry(self):
        client = GeminiClient()
        mock_successful_response = MagicMock()
        mock_successful_response.parsed = {"result": "success"}

        client.client.models.generate_content.side_effect=[
            errors.APIError(500, {}, None),
            mock_successful_response
        ]

        result = await client.generate_content("model", "user", "system")
        self.assertEqual(result, {"result": "success"})
        self.assertEqual(client.client.models.generate_content.call_count, 2)

if __name__ == '__main__':
    unittest.main()
