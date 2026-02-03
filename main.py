import argparse
import logging
import os
import datetime
import asyncio
import sys
from config import Config
from constants import MAX_CONCURRENT_REQUESTS
from pipeline.cache import CacheManager
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer
from pipeline.visualizer import DashboardGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_service_name(csp, service_name):
    """Formats a service name for use in cache keys."""
    return f"{csp}_{service_name}".lower().replace(" ", "_")

async def process_service_item(item, tech_analyst, pricing_analyst, synthesizer, csp_a, csp_b, cache, semaphore):
    async with semaphore:
        service_a = item["csp_a_service_name"]
        service_b = item.get("csp_b_service_name")

        if not service_b:
            logger.info(f"Skipping {service_a} (no match in {csp_b})")
            return None

        formatted_service_a = format_service_name(csp_a, service_a)
        formatted_service_b = format_service_name(csp_b, service_b)
        service_pair_id = f"{formatted_service_a}_vs_{formatted_service_b}"

        logger.info(f"Processing: {service_pair_id}")

        # Technical Analysis
        tech_key = f"technical_{service_pair_id}"
        tech_data = cache.get(tech_key)
        if not tech_data:
            tech_data = await tech_analyst.perform_analysis(csp_a, csp_b, item)
            if tech_data:
                tech_data["service_pair_id"] = service_pair_id
                cache.set(tech_key, tech_data)
            else:
                logger.warning(f"Technical analysis failed for {service_pair_id}")
                return None # Stop processing if analysis fails

        # Pricing Analysis
        pricing_key = f"pricing_{service_pair_id}"
        pricing_data = cache.get(pricing_key)
        if not pricing_data:
            pricing_data = await pricing_analyst.perform_analysis(csp_a, csp_b, item)
            if pricing_data:
                pricing_data["service_pair_id"] = service_pair_id
                cache.set(pricing_key, pricing_data)
            else:
                logger.warning(f"Pricing analysis failed for {service_pair_id}")
                return None

        # Synthesis
        result_key = f"result_{service_pair_id}"
        result_json = cache.get(result_key)
        if not result_json:
            result_json = await synthesizer.synthesize(service_pair_id, tech_data, pricing_data)
            if result_json:
                cache.set(result_key, result_json)
            else:
                logger.warning(f"Synthesis failed for {service_pair_id}")
                return None

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
    parser.add_argument("--clear-cache", action="store_true", help="Clear the cache before running")
    args = parser.parse_args()

    csp_a = args.csp_a
    csp_b = args.csp_b
    test_mode = args.test or Config.TEST_MODE

    # Initialize cache manager
    cache = CacheManager()

    if args.clear_cache:
        logger.info("Clearing cache...")
        cache.clear()
        logger.info("Cache cleared.")


    logger.info(f"Starting pipeline: {csp_a} vs {csp_b} (Test Mode: {test_mode})")

    os.makedirs("public", exist_ok=True)


    # --- Phase 1: Discovery ---
    mapper = ServiceMapper()

    # Step 1: Get service lists for each CSP
    service_list_a_key = f"service_list_{csp_a}"
    service_list_a = cache.get(service_list_a_key)
    if service_list_a and not service_list_a.get("services"):
        logger.warning(f"Cached service list for {csp_a} is empty. Ignoring.")
        service_list_a = None

    if not service_list_a:
        service_list_a = await mapper.get_service_list(csp_a)
        if service_list_a and service_list_a.get("services"):
            cache.set(service_list_a_key, service_list_a)
        else:
            logger.error(f"Failed to retrieve service list for {csp_a}")

    service_list_b_key = f"service_list_{csp_b}"
    service_list_b = cache.get(service_list_b_key)
    if service_list_b and not service_list_b.get("services"):
        logger.warning(f"Cached service list for {csp_b} is empty. Ignoring.")
        service_list_b = None

    if not service_list_b:
        service_list_b = await mapper.get_service_list(csp_b)
        if service_list_b and service_list_b.get("services"):
            cache.set(service_list_b_key, service_list_b)
        else:
            logger.error(f"Failed to retrieve service list for {csp_b}")

    # Step 2: Map services between the two CSPs
    service_map_key = f"service_map_{csp_a}_{csp_b}"
    service_map = cache.get(service_map_key)
    if service_map and not service_map.get("items"):
        logger.warning("Cached service map is empty. Ignoring.")
        service_map = None

    if not service_map:
        # Ensure service lists are valid before mapping
        if service_list_a and service_list_a.get("services") and service_list_b and service_list_b.get("services"):
            service_map = await mapper.map_services(csp_a, csp_b, service_list_a.get('services', []), service_list_b.get('services', []))
            if service_map and service_map.get("items"):
                cache.set(service_map_key, service_map)
            else:
                logger.error("Service mapping failed or returned empty items.")
        else:
            logger.error("Could not retrieve one or both service lists. Aborting.")
            sys.exit(1)

    if not service_map or not service_map.get("items"):
        logger.error("Service mapping failed or produced invalid format. Aborting.")
        sys.exit(1)

    items = service_map.get("items", [])
    if test_mode:
        items = items[:4]
        logger.info(f"Test mode: limiting to {len(items)} services.")

    # --- Phase 2, 3, 4: Analysis, Pricing, Synthesis ---
    tech_analyst = TechnicalAnalyst()
    pricing_analyst = PricingAnalyst()
    synthesizer = Synthesizer()
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    tasks = []
    for item in items:
        tasks.append(process_service_item(item, tech_analyst, pricing_analyst, synthesizer, csp_a, csp_b, cache, semaphore))

    processed_results = await asyncio.gather(*tasks)

    final_results = [res for res in processed_results if res is not None]

    # --- Phase 5: Management Summary ---
    # Group results by domain for the new summary generation
    synthesis_by_domain = {}
    for item in final_results:
        domain = item["map"].get("domain", "Uncategorized")
        if domain not in synthesis_by_domain:
            synthesis_by_domain[domain] = []
        synthesis_by_domain[domain].append(item["result"]["synthesis"])

    # Generate the consolidated management summary
    suffix = "_test" if test_mode else ""
    management_summary_key = f"management_summary_{csp_a}_{csp_b}{suffix}"
    management_summary = cache.get(management_summary_key)

    if not management_summary:
        management_summary = await synthesizer.generate_management_summary(
            synthesis_by_domain
        )
        if management_summary:
            cache.set(management_summary_key, management_summary)
        else:
            logger.warning("Management summary generation failed.")
            management_summary = {} # Ensure it's a dict to avoid template errors

    # --- Phase 6: Visualization ---
    visualizer = DashboardGenerator()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_html = f"public/{csp_a}_{csp_b}_{timestamp}.html"

    visualizer.generate_dashboard(
        csp_a,
        csp_b,
        final_results,
        items,
        management_summary,
        output_html,
    )

    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
