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

# Define mock data at the class level for reuse
mock_technical_data = {
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

mock_pricing_data = {
    "service_pair_id": "EC2_vs_GCE",
    "pricing_models": [
        {"model_type": "On-Demand", "csp_a_details": "Standard hourly rates", "csp_b_details": "Standard hourly rates"}
    ],
    "cost_efficiency_score": 8.0,
    "notes": "Mock pricing data."
}

expected_synthesis = {
    "detailed_comparison": "This is a mock detailed comparison.",
    "executive_summary": "Mock executive summary."
}


class TestPipeline(unittest.IsolatedAsyncioTestCase):

    @patch('pipeline.discovery.genai.Client')
    async def test_discovery(self, MockClient):
        # Setup async mock for the client
        MockClient.return_value.aio.models.generate_content = AsyncMock(
            return_value=MockResponse({"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]})
        )

        # Patch TEST_MODE in the module where it's used to test the real logic path
        with patch('pipeline.discovery.Config.TEST_MODE', False):
            mapper = ServiceMapper()
            # ServiceMapper.__init__ will now use the mock client from the patch
            result = await mapper.discover_services("AWS", "GCP")

            # Verify
            self.assertEqual(result, {"items": [{"domain": "Compute", "csp_a_service_name": "EC2"}]})
            # Check the mock that __init__ would have created and used
            MockClient.return_value.aio.models.generate_content.assert_called_once()
            args, kwargs = MockClient.return_value.aio.models.generate_content.call_args
            self.assertEqual(kwargs['model'], "gemini-3-flash-preview")
            self.assertIn("Analyze the service catalog", kwargs['contents'])

    async def test_analyzer_test_mode(self):
        # Patch TEST_MODE in the module where it is checked
        with patch('pipeline.analyzer.Config.TEST_MODE', True):
            analyst = TechnicalAnalyst()
            service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)
            self.assertEqual(result, mock_technical_data)

    async def test_pricing_test_mode(self):
        # Patch TEST_MODE in the module where it is checked
        with patch('pipeline.pricing_analyst.Config.TEST_MODE', True):
            analyst = PricingAnalyst()
            service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)
            self.assertEqual(result, mock_pricing_data)

    async def test_synthesizer_test_mode(self):
        # Patch TEST_MODE in the module where it is checked
        with patch('pipeline.synthesizer.Config.TEST_MODE', True):
            synthesizer = Synthesizer()
            result = await synthesizer.synthesize("EC2_vs_GCE", mock_technical_data, mock_pricing_data)

            self.assertIn("synthesis", result)
            self.assertEqual(result['synthesis'], expected_synthesis)
            self.assertIn("metadata", result)


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
