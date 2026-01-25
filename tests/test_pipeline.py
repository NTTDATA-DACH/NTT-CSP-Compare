import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
import os
import asyncio
from google.genai import types
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer
from config import Config

# Mock response objects
class MockResponse:
    def __init__(self, parsed_data):
        self.parsed = parsed_data
        self.text = json.dumps(parsed_data)

class TestPipeline(unittest.IsolatedAsyncioTestCase):

    @patch('pipeline.discovery.genai.Client')
    async def test_discovery(self, MockClient):
        # Setup Mock
        mock_client_instance = MockClient.return_value
        mock_client_instance.aio.models.generate_content = AsyncMock(
            return_value=MockResponse({"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]})
        )

        # Run
        mapper = ServiceMapper()
        result = await mapper.discover_services("AWS", "GCP")

        # Verify
        self.assertEqual(result, {"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]})
        mock_client_instance.aio.models.generate_content.assert_called_once()
        args, kwargs = mock_client_instance.aio.models.generate_content.call_args
        self.assertEqual(kwargs['model'], "gemini-3-flash-preview")
        self.assertIn("Analyze the service catalog", kwargs['contents'])

    @patch('pipeline.analyzer.genai.Client')
    async def test_analyzer(self, MockClient):
        mock_client_instance = MockClient.return_value
        expected_data = {
            "service_pair_id": "EC2_vs_GCE",
            "maturity_analysis": "Mature",
            "integration_quality": "High",
            "technical_score": 5,
            "technical_reasoning": "Reason"
        }
        mock_client_instance.aio.models.generate_content = AsyncMock(return_value=MockResponse(expected_data))

        analyst = TechnicalAnalyst()
        service_pair = {
            "csp_a_service_name": "EC2",
            "csp_a_url": "url",
            "csp_b_service_name": "GCE",
            "csp_b_url": "url"
        }
        result = await analyst.perform_analysis("AWS", "GCP", service_pair)

        self.assertEqual(result, expected_data)

        # Verify Thinking and Grounding
        args, kwargs = mock_client_instance.aio.models.generate_content.call_args
        config = kwargs['config']

        # Verify ThinkingConfig
        self.assertIsNotNone(config.thinking_config)

        # Verify Grounding
        self.assertIsNotNone(config.tools)
        self.assertTrue(any(t.google_search is not None for t in config.tools))

    @patch('pipeline.pricing_analyst.genai.Client')
    async def test_pricing(self, MockClient):
        mock_client_instance = MockClient.return_value
        expected_data = {
            "service_pair_id": "EC2_vs_GCE",
            "pricing_models": ["On-Demand"],
            "free_tier_comparison": "None",
            "cost_efficiency_score": 0,
            "pricing_reasoning": "Same"
        }
        mock_client_instance.aio.models.generate_content = AsyncMock(return_value=MockResponse(expected_data))

        analyst = PricingAnalyst()
        service_pair = {
            "csp_a_service_name": "EC2",
            "csp_b_service_name": "GCE"
        }
        result = await analyst.perform_analysis("AWS", "GCP", service_pair)

        self.assertEqual(result, expected_data)

        # Verify Thinking and Grounding
        args, kwargs = mock_client_instance.aio.models.generate_content.call_args
        config = kwargs['config']
        self.assertIsNotNone(config.thinking_config)
        self.assertIsNotNone(config.tools)

    @patch('pipeline.synthesizer.genai.Client')
    def test_synthesizer(self, MockClient):
        mock_client_instance = MockClient.return_value
        mock_models = MagicMock()
        mock_client_instance.models = mock_models

        expected_synthesis = {
            "service_pair_id": "EC2_vs_GCE",
            "detailed_comparison": "Markdown",
            "executive_summary": "Summary"
        }
        mock_models.generate_content.return_value = MockResponse(expected_synthesis)

        synthesizer = Synthesizer()
        result = synthesizer.synthesize("EC2_vs_GCE", {}, {})

        self.assertEqual(result['synthesis'], expected_synthesis)

        # Verify Thinking ONLY (No Grounding)
        args, kwargs = mock_models.generate_content.call_args
        config = kwargs['config']
        self.assertIsNotNone(config.thinking_config)
        self.assertIsNone(config.tools) # Should be None or empty


class TestConfig(unittest.TestCase):

    @patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project-123"})
    def test_gcp_project_id_from_env(self):
        import importlib
        import config
        importlib.reload(config)
        from config import Config as ReloadedConfig
        self.assertEqual(ReloadedConfig.GCP_PROJECT_ID, "test-project-123")

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "fallback-project-456"}, clear=True)
    def test_google_cloud_project_fallback(self):
        # We need to reload the config module to re-evaluate the class variables
        import importlib
        import config
        importlib.reload(config)
        from config import Config as ReloadedConfig
        self.assertEqual(ReloadedConfig.GCP_PROJECT_ID, "fallback-project-456")

if __name__ == '__main__':
    unittest.main()
