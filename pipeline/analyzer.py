import json
import logging
from google import genai
from google.genai import types
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, TECHNICAL_SCHEMA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAnalyst:
    def __init__(self):
        if not Config.TEST_MODE:
            self.client = genai.Client(
                vertexai=True,
                project=Config.GCP_PROJECT_ID,
                location=Config.AI_LOCATION
            ).aio
        else:
            self.client = None
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
                "technical_score": 9.5
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
            # Configure Thinking and Grounding
            # Note: ThinkingConfig location in GenerateContentConfig might vary by version.
            # Based on docs: config=types.GenerateContentConfig(thinking_config=...)

            response = await self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type='application/json',
                    response_schema=self.schema,
                    temperature=0.7, # Thinking models often benefit from non-zero temp
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=False # We usually don't need thoughts in final JSON output unless debugging
                    ),
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
            )

            if hasattr(response, 'parsed') and response.parsed:
                return response.parsed

            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error analyzing {service_a_name} vs {service_b_name}: {e}")
            return None
