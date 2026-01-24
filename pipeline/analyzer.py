import json
import logging
from google import genai
from google.genai import types
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, TECHNICAL_SCHEMA_PATH, THINKING_BUDGET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalAnalyst:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=Config.GCP_PROJECT_ID,
            location=Config.AI_LOCATION
        )
        self.model_name = MODEL_ANALYSIS
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(TECHNICAL_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    def perform_analysis(self, csp_a: str, csp_b: str, service_pair: dict) -> dict:
        service_a_name = service_pair.get("csp_a_service_name")
        service_a_url = service_pair.get("csp_a_url")
        service_b_name = service_pair.get("csp_b_service_name")
        service_b_url = service_pair.get("csp_b_url")

        if not service_b_name:
            logger.warning(f"Skipping analysis for {service_a_name} as no equivalent found in {csp_b}")
            return None

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

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type='application/json',
                    response_schema=self.schema,
                    temperature=0.7, # Thinking models often benefit from non-zero temp
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=False, # We usually don't need thoughts in final JSON output unless debugging
                        thinking_budget=THINKING_BUDGET
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
