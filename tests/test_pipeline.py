import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os
import asyncio
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer
from main import process_service_item, format_service_name

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
    "technical_score": 9.5,
    "technical_reasoning": "<p>This is a mock reasoning.</p>",
    "lockin_analysis": {
        "lockin_score": 5,
        "lockin_reasoning": "<p>This is a mock lock-in reasoning.</p>"
    }
}

mock_pricing_data = {
    "service_pair_id": "EC2_vs_GCE",
    "pricing_models": [
        {"model_type": "On-Demand", "csp_a_details": "Standard hourly rates", "csp_b_details": "Standard hourly rates"}
    ],
    "cost_efficiency_score": 8.0,
    "pricing_reasoning": "<p>This is a detailed mock pricing narrative for testing purposes. It explains that pricing is relatively similar but one has better spot instance availability.</p>"
}

# The expected synthesis result should now be a concatenation of the reasonings
expected_synthesis_detailed = "<h4>Technical Analysis</h4><p>This is a mock reasoning.</p><h4>Lock-in Analysis</h4><p>This is a mock lock-in reasoning.</p><h4>Pricing Analysis</h4><p>This is a detailed mock pricing narrative for testing purposes. It explains that pricing is relatively similar but one has better spot instance availability.</p>"

expected_synthesis = {
    "detailed_comparison": expected_synthesis_detailed
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
            # Pass the mock data to synthesize
            result = await synthesizer.synthesize("EC2_vs_GCE", mock_technical_data, mock_pricing_data)

            # The result object contains more than just the synthesis, let's check that part
            self.assertIn("synthesis", result)
            self.assertEqual(result["synthesis"], expected_synthesis)
            self.assertIn("metadata", result)

    @patch("builtins.open")
    async def test_generate_management_summary(self, mock_open):
        mock_open.return_value.__enter__.return_value.read.return_value = "{}"
        with patch("pipeline.synthesizer.Config.TEST_MODE", True):
            synthesizer = Synthesizer()
            result = await synthesizer.generate_management_summary({"Compute": [{}]})

            self.assertIn("overarching_summary", result)
            self.assertIn("domain_summaries", result)
            self.assertIn("Compute", result["domain_summaries"])

    def test_format_service_name(self):
        self.assertEqual(format_service_name("AWS", "EC2"), "aws_ec2")
        self.assertEqual(format_service_name("GCP", "Compute Engine"), "gcp_compute_engine")

    async def test_process_service_item_caching_collision(self):
        # Mocks for dependencies
        tech_analyst = MagicMock()
        pricing_analyst = MagicMock()
        synthesizer = MagicMock()
        cache = MagicMock()
        semaphore = asyncio.Semaphore(1)

        # Mock return values for async methods
        tech_analyst.perform_analysis = AsyncMock(return_value={"tech_data": "some_data"})
        pricing_analyst.perform_analysis = AsyncMock(return_value={"pricing_data": "some_data"})
        synthesizer.synthesize = AsyncMock(return_value={"synthesis": "some_synthesis"})

        # Item 1: AWS "Compute" service vs GCP "Compute Engine"
        item1 = {"csp_a_service_name": "Compute", "csp_b_service_name": "Compute Engine"}
        csp_a1, csp_b1 = "AWS", "GCP"

        # Item 2: Azure "Compute" service vs GCP "Compute Engine" (same service names, different csp_a)
        item2 = {"csp_a_service_name": "Compute", "csp_b_service_name": "Compute Engine"}
        csp_a2, csp_b2 = "Azure", "GCP"

        # Simulate cache misses for both
        cache.get.return_value = None

        # Process both items
        await process_service_item(item1, tech_analyst, pricing_analyst, synthesizer, csp_a1, csp_b1, cache, semaphore)
        await process_service_item(item2, tech_analyst, pricing_analyst, synthesizer, csp_a2, csp_b2, cache, semaphore)

        # Get the keys used for caching
        tech_key1_call = cache.set.call_args_list[0][0][0]
        tech_key2_call = cache.set.call_args_list[3][0][0] # 3 because each process_service_item calls cache.set 3 times

        # Assert that the keys are different
        self.assertNotEqual(tech_key1_call, tech_key2_call, "Cache keys for services with the same name but different CSPs should be different.")


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
