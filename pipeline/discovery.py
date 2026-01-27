import asyncio
import json
import logging
from config import Config
from constants import MAX_CONCURRENT_REQUESTS, MODEL_DISCOVERY, PROMPT_CONFIG_PATH, SERVICE_LIST_SCHEMA_PATH, SERVICE_MAP_SINGLE_SCHEMA_PATH
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

        with open(SERVICE_LIST_SCHEMA_PATH, 'r') as f:
            self.service_list_schema = json.load(f)

        with open(SERVICE_MAP_SINGLE_SCHEMA_PATH, 'r') as f:
            self.single_schema = json.load(f)

    async def get_service_list(self, csp: str) -> dict:
        """
        Gets a list of services for a single CSP.
        """

        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for ServiceMapper. Returning mock service list for {csp}.")
            if csp == "AWS":
                return {
                    "services": [
                        {"service_name": "EC2", "service_url": "https://aws.amazon.com/ec2/", "description": "Virtual Servers in the Cloud"},
                        {"service_name": "S3", "service_url": "https://aws.amazon.com/s3/", "description": "Object Storage Built to Store and Retrieve Any Amount of Data from Anywhere"},
                        {"service_name": "RDS", "service_url": "https://aws.amazon.com/rds/", "description": "Managed Relational Database Service for MySQL, PostgreSQL, Oracle, SQL Server, and MariaDB"}
                    ]
                }
            else:
                 return {
                    "services": [
                        {"service_name": "Compute Engine", "service_url": "https://cloud.google.com/compute/", "description": "Virtual Machines Running in Google's Data Center"},
                        {"service_name": "Cloud Storage", "service_url": "https://cloud.google.com/storage/", "description": "Object Storage for Companies of All Sizes"}
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

    async def _map_single_service(self, service_a: dict, services_b: list, csp_a: str, csp_b: str, semaphore: asyncio.Semaphore) -> dict:
        """
        Finds the best match for a single service from CSP A in the list of services from CSP B.
        """
        async with semaphore:
            service_name_a = service_a.get("service_name", "Unknown Service")
            logger.info(f"Finding match for {service_name_a} in {csp_b}")

            prompt_config = self.prompts.get("service_map_single_prompt", {})
            system_instruction = prompt_config.get("system_instruction")
            user_template = prompt_config.get("user_template")

            if not all([system_instruction, user_template]):
                logger.error("Missing prompt configuration for single service mapping.")
                return {
                    "domain": service_a.get("domain", "Unknown"),
                    "csp_a_service_name": service_name_a,
                    "csp_a_url": service_a.get("service_url", ""),
                    "csp_b_service_name": None,
                    "csp_b_url": None
                }

            user_content = user_template.format(
                csp_a=csp_a,
                csp_b=csp_b,
                service_a=json.dumps(service_a),
                services_b=json.dumps(services_b)
            )

            try:
                response = await self.client.generate_content(
                    model_name=self.model_name,
                    user_content=user_content,
                    system_instruction=system_instruction,
                    schema=self.single_schema
                )
                if response is None:
                    logger.warning(f"No match found for {service_name_a}")
                    return {
                        "domain": service_a.get("domain", "Unknown"),
                        "csp_a_service_name": service_name_a,
                        "csp_a_url": service_a.get("service_url", ""),
                        "csp_b_service_name": None,
                        "csp_b_url": None
                    }
                return response
            except Exception as e:
                logger.error(f"Error matching service {service_name_a}: {e}")
                return {
                    "domain": service_a.get("domain", "Unknown"),
                    "csp_a_service_name": service_name_a,
                    "csp_a_url": service_a.get("service_url", ""),
                    "csp_b_service_name": None,
                    "csp_b_url": None
                }

    async def map_services(self, csp_a: str, csp_b: str, services_a: list, services_b: list) -> dict:
        """
        Maps services from CSP A to CSP B by finding the best match for each service individually.
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

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = [self._map_single_service(service_a, services_b, csp_a, csp_b, semaphore) for service_a in services_a]
        mapped_services = await asyncio.gather(*tasks)

        return {"items": mapped_services}
