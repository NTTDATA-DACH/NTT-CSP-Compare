import json
import logging
import os
from google import genai
from google.genai import types
from config import Config
from constants import MODEL_DISCOVERY, PROMPT_CONFIG_PATH, SERVICE_MAP_SCHEMA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceMapper:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=Config.GCP_PROJECT_ID,
            location=Config.AI_LOCATION
        )
        self.model_name = MODEL_DISCOVERY
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(SERVICE_MAP_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    def discover_services(self, csp_a: str, csp_b: str) -> dict:
        """
        Maps services from CSP A to CSP B using Gemini 3 Flash.
        """
        logger.info(f"Starting discovery: {csp_a} -> {csp_b} using {self.model_name}")

        prompt_config = self.prompts["discovery_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(csp_a=csp_a, csp_b=csp_b)

        # For testing purposes, if TEST_MODE is on, we might want to inject a simpler prompt
        # or limit the scope, but the LLM should handle it.
        # The project spec says TEST=true limits processing to top 3 services.
        # This limit logic might need to be applied AFTER discovery or IN the prompt.
        # "true limits processing to top 3 services" usually means downstream.
        # But if the discovery returns 100 services, we iterate only 3.
        # So discovery can return full list.

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type='application/json',
                    response_schema=self.schema,
                    temperature=0.1, # Deterministic
                )
            )

            if not response.text:
                logger.error("Empty response from Discovery model.")
                return {"items": []}

            # Verify and parse JSON
            # The SDK might parse it automatically if we access response.parsed?
            # PyPI doc says: print(response.parsed)

            if hasattr(response, 'parsed') and response.parsed:
                return response.parsed

            # Fallback to text parsing
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            # Return empty structure or raise
            return {"items": []}

if __name__ == "__main__":
    # Local test
    mapper = ServiceMapper()
    result = mapper.discover_services("AWS", "GCP")
    print(json.dumps(result, indent=2))
