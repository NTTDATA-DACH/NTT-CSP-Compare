import json
import logging
import datetime
from unittest.mock import AsyncMock
from google import genai
from google.genai import types
from config import Config
from constants import (
    MODEL_SYNTHESIS,
    PROMPT_CONFIG_PATH,
    SYNTHESIS_SCHEMA_PATH,
    MANAGEMENT_SUMMARY_SCHEMA_PATH,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Synthesizer:
    def __init__(self):
        self.client = (
            genai.Client(
                vertexai=True,
                project=Config.GCP_PROJECT_ID,
                location=Config.AI_LOCATION,
            ).aio
            if not Config.TEST_MODE
            else AsyncMock()
        )
        self.model_name = MODEL_SYNTHESIS
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, "r") as f:
            self.prompts = json.load(f)

        with open(SYNTHESIS_SCHEMA_PATH, "r") as f:
            self.schema = json.load(f)

        with open(MANAGEMENT_SUMMARY_SCHEMA_PATH, "r") as f:
            self.management_summary_schema = json.load(f)

    async def summarize_by_domain(self, domain_name: str, synthesis_results: list) -> dict:
        if not synthesis_results:
            return None

        if Config.TEST_MODE:
            logger.info(
                f"TEST_MODE enabled. Returning mock management summary for {domain_name}"
            )
            return {
                "management_summary": f"This is a mock management summary for the {domain_name} domain."
            }

        prompt_config = self.prompts["management_summary_prompt"]
        system_instruction = prompt_config["system_instruction"]
        synthesis_str = json.dumps(synthesis_results)

        user_content = prompt_config["user_template"].format(
            domain_name=domain_name, synthesis_json=synthesis_str
        )

        try:
            response = await self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=self.management_summary_schema,
                    temperature=0.7,
                ),
            )

            if hasattr(response, "parsed") and response.parsed:
                return response.parsed
            else:
                return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error generating management summary for {domain_name}: {e}")
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
            response = await self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type='application/json',
                    response_schema=self.schema,
                    temperature=0.7,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=False,
                    )
                    # No Grounding for synthesis
                )
            )

            synthesis_result = None
            if hasattr(response, 'parsed') and response.parsed:
                synthesis_result = response.parsed
            else:
                synthesis_result = json.loads(response.text)

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
