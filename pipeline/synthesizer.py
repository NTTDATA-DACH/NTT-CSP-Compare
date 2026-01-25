import json
import logging
import datetime
from unittest.mock import AsyncMock
from google import genai
from google.genai import types
from config import Config
from constants import MODEL_SYNTHESIS, PROMPT_CONFIG_PATH, SYNTHESIS_SCHEMA_PATH

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
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(SYNTHESIS_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    async def synthesize(self, service_pair_id: str, technical_data: dict, pricing_data: dict) -> dict:
        """
        Synthesizes technical and pricing analysis into a narrative.
        Returns the Result object (Technical + Pricing + Synthesis).
        """
        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for Synthesizer. Returning mock data for {service_pair_id}")
            synthesis_result = {
                "strengths_csp_a": ["- Mock strength A1", "- Mock strength A2"],
                "strengths_csp_b": ["- Mock strength B1", "- Mock strength B2"],
                "weaknesses_csp_a": ["- Mock weakness A1"],
                "weaknesses_csp_b": ["- Mock weakness B1"],
                "final_recommendation": "Mock recommendation.",
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
        tech_str = json.dumps(technical_data, indent=2)
        price_str = json.dumps(pricing_data, indent=2)

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
