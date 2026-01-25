import json
import logging
import datetime
from unittest.mock import AsyncMock
from google import genai
from google.genai import types
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiClient:
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

    async def generate_content(self, model_name: str, user_content: str, system_instruction: str, schema: dict = None, enable_grounding: bool = True) -> dict:
        system_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
        timed_system_instruction = f"Today is {system_time}. Use this date as the reference point for all Google Search queries.\n\n{system_instruction}"

        tools = [types.Tool(google_search=types.GoogleSearch())] if enable_grounding else []

        try:
            response = await self.client.models.generate_content(
                model=model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    tools=tools,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level="HIGH"
                    ),
                    temperature=1.0,
                    system_instruction=timed_system_instruction,
                    response_mime_type='application/json',
                    response_schema=schema,
                )
            )

            if hasattr(response, 'parsed') and response.parsed:
                return response.parsed

            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error generating content with model {model_name}: {e}")
            return None
