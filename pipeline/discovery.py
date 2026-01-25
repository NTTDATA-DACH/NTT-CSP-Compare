import json
import logging
from config import Config
from constants import MODEL_DISCOVERY, PROMPT_CONFIG_PATH, SERVICE_MAP_SCHEMA_PATH, SERVICE_LIST_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceMapper:
    def __init__(self):
        self.client = GeminiClient()
        self.model_name = MODEL_DISCOVERY
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(SERVICE_MAP_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

        with open(SERVICE_LIST_SCHEMA_PATH, 'r') as f:
            self.service_list_schema = json.load(f)

    async def get_service_list(self, csp: str) -> dict:
        """
        Gets a list of services for a single CSP.
        """

        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for ServiceMapper. Returning mock service list for {csp}.")
            if csp == "AWS":
                return {
                    "services": [
                        {"service_name": "EC2", "service_url": "https://aws.amazon.com/ec2/"},
                        {"service_name": "S3", "service_url": "https://aws.amazon.com/s3/"},
                        {"service_name": "RDS", "service_url": "https://aws.amazon.com/rds/"}
                    ]
                }
            else:
                 return {
                    "services": [
                        {"service_name": "Compute Engine", "service_url": "https://cloud.google.com/compute/"},
                        {"service_name": "Cloud Storage", "service_url": "https://cloud.google.com/storage/"}
                    ]
                }

        logger.info(f"Getting service list for {csp} using {self.model_name}")

        prompt_config = self.prompts["service_list_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(csp=csp)

        try:
            response = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.service_list_schema
            )
            if response is None:
                logger.error(f"Received None response from GeminiClient for {csp}")
                return {"services": []}
            return response
        except Exception as e:
            logger.error(f"Error getting service list for {csp}: {e}")
            return {"services": []}

    async def map_services(self, csp_a: str, csp_b: str, services_a: list, services_b: list) -> dict:
        """
        Maps services from CSP A to CSP B using Gemini 3 Flash.
        """

        if Config.TEST_MODE:
            logger.info("TEST_MODE enabled for ServiceMapper. Returning mock data.")
            return {
                "items": [
                    {
                        "domain": "Compute",
                        "csp_a_service_name": "EC2",
                        "csp_a_url": "https://aws.amazon.com/ec2/",
                        "csp_b_service_name": "Compute Engine",
                        "csp_b_url": "https://cloud.google.com/compute/"
                    },
                    {
                        "domain": "Storage",
                        "csp_a_service_name": "S3",
                        "csp_a_url": "https://aws.amazon.com/s3/",
                        "csp_b_service_name": "Cloud Storage",
                        "csp_b_url": "https://cloud.google.com/storage/"
                    },
                    {
                        "domain": "Database",
                        "csp_a_service_name": "RDS",
                        "csp_a_url": "https://aws.amazon.com/rds/",
                        "csp_b_service_name": ""
                    }
                ]
            }

        logger.info(f"Starting service mapping: {csp_a} -> {csp_b} using {self.model_name}")

        prompt_config = self.prompts["service_map_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(
            csp_a=csp_a,
            csp_b=csp_b,
            services_a=json.dumps(services_a),
            services_b=json.dumps(services_b)
        )

        try:
            response = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.schema
            )
            if response is None:
                logger.error(f"Received None response from GeminiClient during service mapping for {csp_a} to {csp_b}")
                return {"items": []}
            return response

        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            return {"items": []}
