import json
import logging
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, PRICING_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PricingAnalyst:
    def __init__(self):
        self.client = GeminiClient()
        self.model_name = MODEL_ANALYSIS # Reuse the same model (Pro Thinking)
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(PRICING_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    async def perform_analysis(self, csp_a: str, csp_b: str, service_pair: dict) -> dict:
        service_a_name = service_pair.get("csp_a_service_name")
        service_b_name = service_pair.get("csp_b_service_name")

        if not service_b_name:
            logger.warning(f"Skipping pricing analysis for {service_a_name} as no equivalent found in {csp_b}")
            return None

        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for PricingAnalyst. Returning mock data for {service_a_name} vs {service_b_name}")
            return {
                "service_pair_id": f"{service_a_name}_vs_{service_b_name}",
                "pricing_models": [
                    {"model_type": "On-Demand", "csp_a_details": "Standard hourly rates", "csp_b_details": "Standard hourly rates"}
                ],
                "cost_efficiency_score": 8.0,
                "pricing_reasoning": "This is a detailed mock pricing narrative for testing purposes. It explains that pricing is relatively similar but one has better spot instance availability."
            }

        prompt_config = self.prompts["pricing_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(
            csp_a=csp_a,
            service_a_name=service_a_name,
            csp_b=csp_b,
            service_b_name=service_b_name
        )

        try:
            response = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.schema
            )
            if response is None:
                logger.error(f"Received None response from GeminiClient for {service_a_name} vs {service_b_name}")
                return None
            return response

        except Exception as e:
            logger.error(f"Error analyzing pricing for {service_a_name} vs {service_b_name}: {e}")
            return None
