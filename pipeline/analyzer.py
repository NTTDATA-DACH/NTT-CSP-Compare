import json
import logging
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, TECHNICAL_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAnalyst:
    def __init__(self):
        self.client = GeminiClient()
        self.model_name = MODEL_ANALYSIS
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(TECHNICAL_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    async def perform_analysis(self, csp_a: str, csp_b: str, service_pair: dict) -> dict:
        service_a_name = service_pair.get("csp_a_service_name")
        service_a_url = service_pair.get("csp_a_url")
        service_b_name = service_pair.get("csp_b_service_name")
        service_b_url = service_pair.get("csp_b_url")

        if not service_b_name:
            logger.warning(f"Skipping analysis for {service_a_name} as no equivalent found in {csp_b}")
            return None

        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for TechnicalAnalyst. Returning mock data for {service_a_name} vs {service_b_name}")
            return {
                "service_pair_id": f"{service_a_name}_vs_{service_b_name}",
                "maturity_analysis": {
                    "csp_a": {"stability": "High", "release_stage": "GA", "feature_completeness": "High"},
                    "csp_b": {"stability": "High", "release_stage": "GA", "feature_completeness": "High"}
                },
                "integration_quality": {
                    "api_consistency": "Good", "documentation_quality": "Excellent", "sdk_support": "Broad"
                },
                "technical_score": 9.5,
                "open_standard": "This is a mock open standard analysis."
            }

        prompt_config = self.prompts["technical_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(
            csp_a=csp_a,
            service_a_name=service_a_name,
            service_a_url=service_a_url,
            csp_b=csp_b,
            service_b_name=service_b_name,
            service_b_url=service_b_url
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
            logger.error(f"Error analyzing {service_a_name} vs {service_b_name}: {e}")
            return None
