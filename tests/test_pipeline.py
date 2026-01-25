import unittest
from unittest.mock import patch
import json
import os
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer

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
    "detailed_comparison": "Mock detailed comparison.",
    "executive_summary": "Mock executive summary."
}

class TestPipeline(unittest.IsolatedAsyncioTestCase):
    @patch("builtins.open")
    async def test_discovery(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = "{}"
        with patch('pipeline.discovery.Config.TEST_MODE', True):
            mapper = ServiceMapper()
            # In test mode, discover_services returns a hardcoded mock object.
            # The client is not used, so we don't need to mock it.
            services_a = await mapper.get_service_list("AWS")
            services_b = await mapper.get_service_list("GCP")
            result = await mapper.map_services("AWS", "GCP", services_a['services'], services_b['services'])

            # Verify that the mock data is returned
            self.assertIn("items", result)
            self.assertEqual(result["items"][0]["csp_a_service_name"], "EC2")

    async def test_analyzer_test_mode(self):
        # Patch TEST_MODE in the module where it is checked
        with patch('pipeline.analyzer.Config.TEST_MODE', True):
            analyst = TechnicalAnalyst()
            service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)
            expected_data = mock_technical_data.copy()
            self.assertEqual(result, expected_data)

    async def test_pricing(self):
        # This test now validates that TEST_MODE returns the correct mock data.
        with patch('pipeline.pricing_analyst.Config.TEST_MODE', True):
            analyst = PricingAnalyst()
            service_pair = {"csp_a_service_name": "EC2", "csp_b_service_name": "GCE"}
            result = await analyst.perform_analysis("AWS", "GCP", service_pair)
            expected_data = mock_pricing_data.copy()
            self.assertEqual(result, expected_data)

    @patch("builtins.open")
    async def test_synthesizer(self, mock_open):
        # This test now validates that TEST_MODE returns the correct mock data.
        mock_open.return_value.__enter__.return_value.read.return_value = "{}"
        with patch("pipeline.synthesizer.Config.TEST_MODE", True):
            synthesizer = Synthesizer()
            result = await synthesizer.synthesize("EC2_vs_GCE", {}, {})

            # The result object contains more than just the synthesis, let's check that part
            self.assertIn("synthesis", result)
            self.assertEqual(result["synthesis"], expected_synthesis)
            self.assertIn("metadata", result)

    @patch("builtins.open")
    async def test_summarize_by_domain(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = "{}"
        with patch("pipeline.synthesizer.Config.TEST_MODE", True):
            synthesizer = Synthesizer()
            result = await synthesizer.summarize_by_domain("Compute", [{}])

            self.assertIn("management_summary", result)
            self.assertEqual(
                result["management_summary"],
                "This is a mock management summary for the Compute domain.",
            )


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
