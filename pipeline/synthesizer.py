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

        # Removed SYNTHESIS_SCHEMA_PATH usage as per-pair synthesis is now deterministic concatenation

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
        Now purely concatenates the detailed narratives from previous steps into an HTML block.
        """
        tech_reasoning = technical_data.get("technical_reasoning", "<p>No technical reasoning provided.</p>")

        lockin_data = technical_data.get("lockin_analysis", {})
        lockin_reasoning = lockin_data.get("lockin_reasoning", "<p>No lock-in reasoning provided.</p>")

        pricing_reasoning = pricing_data.get("pricing_reasoning", "<p>No pricing reasoning provided.</p>")

        # Concatenate narratives for the detailed comparison
        detailed_comparison = (
            f"<h4>Technical Analysis</h4>{tech_reasoning}"
            f"<h4>Lock-in Analysis</h4>{lockin_reasoning}"
            f"<h4>Pricing Analysis</h4>{pricing_reasoning}"
        )

        synthesis_result = {
            "detailed_comparison": detailed_comparison
        }

        if Config.TEST_MODE:
            logger.info(
                f"TEST_MODE enabled for Synthesizer. Returning mock data for {service_pair_id}"
            )
            # In TEST_MODE, we also just return the concatenated structure,
            # assuming upstream components provide mock data that fits.
            # If not, we can force a mock string here, but better to use the inputs if available.
            pass # Use the same logic for test mode as production since it's just string concatenation

        # Construct final Result object
        result = {
            "metadata": {
                "service_pair_id": service_pair_id,
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "model_version": "deterministic_concatenation" # No model used
            },
            "technical_data": technical_data,
            "pricing_data": pricing_data,
            "synthesis": synthesis_result
        }
        return result
