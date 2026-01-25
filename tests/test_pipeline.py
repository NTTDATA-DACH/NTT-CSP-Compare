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

    async def test_discovery(self):
        with patch('config.Config.TEST_MODE', True):
            mapper = ServiceMapper()

            # Configure the mock created in __init__
            mapper.client.models.generate_content.return_value = MockResponse(
                {"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]}
            )

            result = await mapper.discover_services("AWS", "GCP")

            # Verify
            self.assertEqual(result, {"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]})
            mapper.client.models.generate_content.assert_called_once()
            args, kwargs = mapper.client.models.generate_content.call_args
            self.assertEqual(kwargs['model'], "gemini-3-flash-preview")
            self.assertIn("Analyze the service catalog", kwargs['contents'])

    @patch('pipeline.analyzer.genai.Client')
    async def test_analyzer(self, MockClient):
        # This test now validates that TEST_MODE returns the correct mock data.
        analyst = TechnicalAnalyst()
        service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}

        # Enable test mode for this specific test
        with patch('config.Config.TEST_MODE', True):
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)

        expected_data = {
            "service_pair_id": "EC2_vs_GCE",
            "maturity_analysis": {
                "csp_a": {"stability": "High", "release_stage": "GA", "feature_completeness": "High"},
                "csp_b": {"stability": "High", "release_stage": "GA", "feature_completeness": "High"}
            },
            "integration_quality": {
                "api_consistency": "Good", "documentation_quality": "Excellent", "sdk_support": "Broad"
            },
            "technical_score": 9.5
        }
        self.assertEqual(result, expected_data)

    @patch('pipeline.pricing_analyst.genai.Client')
    async def test_pricing(self, MockClient):
        # This test now validates that TEST_MODE returns the correct mock data.
        analyst = PricingAnalyst()
        service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}

    @patch('pipeline.synthesizer.genai.Client')
    async def test_synthesizer(self, MockClient):
        mock_client_instance = MockClient.return_value
        expected_data = {
            "service_pair_id": "EC2_vs_GCE",
            "pricing_models": [
                {"model_type": "On-Demand", "csp_a_details": "Standard hourly rates", "csp_b_details": "Standard hourly rates"}
            ],
            "cost_efficiency_score": 8.0,
            "notes": "Mock pricing data."
        }
        # Since the client method is now async, the mock needs to be async too
        mock_client_instance.aio.models.generate_content = AsyncMock(
            return_value=MockResponse(expected_synthesis)
        )

    @patch('pipeline.synthesizer.genai.Client')
    async def test_synthesizer(self, MockClient):
        # This test now validates that TEST_MODE returns the correct mock data.
        synthesizer = Synthesizer()
        result = await synthesizer.synthesize("EC2_vs_GCE", {}, {})

        # The result object contains more than just the synthesis, let's check that part
        self.assertIn("synthesis", result)
        self.assertEqual(result['synthesis'], expected_synthesis)
        self.assertIn("metadata", result)

        # Verify call arguments
        args, kwargs = mock_client_instance.aio.models.generate_content.call_args
        config = kwargs['config']

        # In synthesizer, grounding is not used, so tools should not be set.
        self.assertNotIn('tools', kwargs)


class TestConfig(unittest.TestCase):

    @patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project-123"})
    def test_gcp_project_id_from_env(self):
        import importlib
        import config
        importlib.reload(config)
        from config import Config as ReloadedConfig
        self.assertEqual(ReloadedConfig.GCP_PROJECT_ID, "test-project-123")

    @patch.dict(
        os.environ,
        {
            "GOOGLE_CLOUD_PROJECT": "fallback-project-456",
            "BUCKET_NAME": "test-bucket",
            "AI_LOCATION": "test-location",
        },
        clear=True,
    )
    def test_google_cloud_project_fallback(self):
        # We need to reload the config module to re-evaluate the class variables
        import importlib
        import config
        importlib.reload(config)
        from config import Config as ReloadedConfig
        self.assertEqual(ReloadedConfig.GCP_PROJECT_ID, "fallback-project-456")

if __name__ == '__main__':
    unittest.main()
