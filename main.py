import argparse
import logging
import json
import os
import datetime
import asyncio
from config import Config
from constants import MAX_CONCURRENT_REQUESTS
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer
from pipeline.visualizer import DashboardGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_service_item(item, tech_analyst, pricing_analyst, synthesizer, csp_a, csp_b, semaphore):
    async with semaphore:
        service_a = item["csp_a_service_name"]
        service_b = item.get("csp_b_service_name")

        if not service_b:
            logger.info(f"Skipping {service_a} (no match in {csp_b})")
            return None

        service_pair_id = f"{service_a}_vs_{service_b}"
        logger.info(f"Processing: {service_pair_id}")

        # Perform analyses
        tech_data = await tech_analyst.perform_analysis(csp_a, csp_b, item)
        if not tech_data:
            logger.warning(f"Technical analysis failed for {service_pair_id}")
            return None
        tech_data["service_pair_id"] = service_pair_id
        with open(f"data/technical_{service_pair_id}.json", "w") as f:
            json.dump(tech_data, f, indent=2)

        pricing_data = await pricing_analyst.perform_analysis(csp_a, csp_b, item)
        if not pricing_data:
            logger.warning(f"Pricing analysis failed for {service_pair_id}")
            return None
        pricing_data["service_pair_id"] = service_pair_id
        with open(f"data/pricing_{service_pair_id}.json", "w") as f:
            json.dump(pricing_data, f, indent=2)

        # Synthesis
        result_json = await synthesizer.synthesize(service_pair_id, tech_data, pricing_data)
        if not result_json:
            logger.warning(f"Synthesis failed for {service_pair_id}")
            return None
        with open(f"data/result_{service_pair_id}.json", "w") as f:
            json.dump(result_json, f, indent=2)

        # Return combined result for visualization
        return {
            "map": item,
            "result": result_json
        }

async def main():
    parser = argparse.ArgumentParser(description="Cloud Service Provider Comparator Pipeline")
    parser.add_argument("--csp-a", required=True, help="First CSP (e.g., AWS)")
    parser.add_argument("--csp-b", required=True, help="Second CSP (e.g., GCP)")
    parser.add_argument("--test", action="store_true", help="Run in test mode (limit to 3 services)")
    args = parser.parse_args()

    csp_a = args.csp_a
    csp_b = args.csp_b
    test_mode = args.test or Config.TEST_MODE

    logger.info(f"Starting pipeline: {csp_a} vs {csp_b} (Test Mode: {test_mode})")

    # Ensure data directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("public", exist_ok=True)

    # --- Phase 1: Discovery ---
    mapper = ServiceMapper()
    service_map = await mapper.discover_services(csp_a, csp_b)

    # Save Service Map
    with open(f"data/service_map_{csp_a}_{csp_b}.json", "w") as f:
        json.dump(service_map, f, indent=2)

    items = service_map.get("items", [])
    if test_mode:
        items = items[:3]
        logger.info(f"Test mode: limiting to {len(items)} services.")

    # --- Phase 2, 3, 4: Analysis, Pricing, Synthesis ---
    tech_analyst = TechnicalAnalyst()
    pricing_analyst = PricingAnalyst()
    synthesizer = Synthesizer()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = []
    for item in items:
        tasks.append(process_service_item(item, tech_analyst, pricing_analyst, synthesizer, csp_a, csp_b, semaphore))

    processed_results = await asyncio.gather(*tasks)

    final_results = [res for res in processed_results if res is not None]

    # --- Phase 5: Visualization ---
    visualizer = DashboardGenerator()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_html = f"public/{csp_a}_{csp_b}_{timestamp}.html"

    visualizer.generate_dashboard(csp_a, csp_b, final_results, items, output_html)

    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
