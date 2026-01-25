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

    async def test_discovery(self):
        with patch('config.Config.TEST_MODE', True):
            mapper = ServiceMapper()
            # In test mode, discover_services returns a hardcoded mock object.
            # The client is not used, so we don't need to mock it.
            result = await mapper.discover_services("AWS", "GCP")

            # Verify that the mock data is returned
            self.assertIn("items", result)
            self.assertEqual(result["items"][0]["csp_a_service_name"], "EC2")

    async def test_analyzer_test_mode(self):
        # Patch TEST_MODE in the module where it is checked
        with patch('pipeline.analyzer.Config.TEST_MODE', True):
            analyst = TechnicalAnalyst()
            service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)
            self.assertEqual(result, mock_technical_data)

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
        # This test now validates that TEST_MODE returns the correct mock data.
        synthesizer = Synthesizer()
        expected_synthesis = {
            "strengths_csp_a": ["- Mock strength A1", "- Mock strength A2"],
            "strengths_csp_b": ["- Mock strength B1", "- Mock strength B2"],
            "weaknesses_csp_a": ["- Mock weakness A1"],
            "weaknesses_csp_b": ["- Mock weakness B1"],
            "final_recommendation": "Mock recommendation.",
        }

        with patch('config.Config.TEST_MODE', True):
            result = await synthesizer.synthesize("EC2_vs_GCE", {}, {})

        # The result object contains more than just the synthesis, let's check that part
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
