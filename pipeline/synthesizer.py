import json
import logging
import datetime
from config import Config
from constants import (
    MODEL_SYNTHESIS,
    PROMPT_CONFIG_PATH,
    SYNTHESIS_SCHEMA_PATH,
    MANAGEMENT_SUMMARY_SCHEMA_PATH,
    OVERARCHING_SUMMARY_SCHEMA_PATH,
)
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Synthesizer:
    def __init__(self):
        self.client = GeminiClient()
        self.model_name = MODEL_SYNTHESIS
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, "r") as f:
            self.prompts = json.load(f)

        with open(SYNTHESIS_SCHEMA_PATH, "r") as f:
            self.schema = json.load(f)

        with open(MANAGEMENT_SUMMARY_SCHEMA_PATH, "r") as f:
            self.management_summary_schema = json.load(f)

    async def generate_management_summary(self, synthesis_by_domain: dict) -> dict:
        if not synthesis_by_domain:
            return None

        if Config.TEST_MODE:
            logger.info("TEST_MODE enabled. Returning mock management summary.")
            return {
                "overarching_summary": "This is a mock overarching summary.",
                "domain_summaries": {
                    "Compute": "Mock summary for Compute.",
                    "Storage": "Mock summary for Storage.",
                },
            }

        prompt_config = self.prompts["management_summary_prompt"]
        system_instruction = prompt_config["system_instruction"]
        synthesis_str = json.dumps(synthesis_by_domain)

        user_content = prompt_config["user_template"].format(
            synthesis_json=synthesis_str
        )

        try:
            response = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.management_summary_schema,
                enable_grounding=False,
            )
            if response is None:
                logger.error("Received None response from GeminiClient for management summary")
                return None
            return response

        except Exception as e:
            logger.error(f"Error generating management summary: {e}")
            return None
    async def synthesize(
        self, service_pair_id: str, technical_data: dict, pricing_data: dict
    ) -> dict:
        """
        Synthesizes technical and pricing analysis into a narrative.
        Returns the Result object (Technical + Pricing + Synthesis).
        """
        if Config.TEST_MODE:
            logger.info(
                f"TEST_MODE enabled for Synthesizer. Returning mock data for {service_pair_id}"
            )
            synthesis_result = {
                "executive_summary": "Mock executive summary.",
                "detailed_comparison": "Mock detailed comparison.",
            }
            return {
                "metadata": {
                    "service_pair_id": service_pair_id,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "model_version": self.model_name
                },
                "technical_data": technical_data,
                "pricing_data": pricing_data,
                "synthesis": synthesis_result
            }

        prompt_config = self.prompts["synthesis_prompt"]
        system_instruction = prompt_config["system_instruction"]

        # Serialize inputs for the prompt
        tech_str = json.dumps(technical_data)
        price_str = json.dumps(pricing_data)

        user_content = prompt_config["user_template"].format(
            service_pair_id=service_pair_id,
            technical_json=tech_str,
            pricing_json=price_str
        )

        try:
            synthesis_result = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.schema,
                enable_grounding=False
            )

            if synthesis_result is None:
                logger.error(f"Received None response from GeminiClient for {service_pair_id}")
                return None

            # Construct final Result object
            result = {
                "metadata": {
                    "service_pair_id": service_pair_id,
                    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "model_version": self.model_name
                },
                "technical_data": technical_data,
                "pricing_data": pricing_data,
                "synthesis": synthesis_result
            }
            return result

        except Exception as e:
            logger.error(f"Error synthesizing {service_pair_id}: {e}")
            return None
