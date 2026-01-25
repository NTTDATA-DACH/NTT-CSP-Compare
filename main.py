import argparse
import logging
import json
import os
import datetime
import asyncio
import sys
import time
from config import Config
from constants import MAX_CONCURRENT_REQUESTS
from pipeline.discovery import ServiceMapper
from pipeline.analyzer import TechnicalAnalyst
from pipeline.pricing_analyst import PricingAnalyst
from pipeline.synthesizer import Synthesizer
from pipeline.visualizer import DashboardGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_cached_data(filepath, max_age_days=7):
    """
    Checks if a file exists and is recent enough.
    Returns the parsed JSON data if valid, None otherwise.
    """
    if not os.path.exists(filepath):
        return None

    try:
        file_age = time.time() - os.path.getmtime(filepath)
        max_age_seconds = max_age_days * 24 * 60 * 60

        if file_age > max_age_seconds:
            logger.info(f"Cache expired for {filepath} (Age: {file_age/86400:.1f} days)")
            return None

        with open(filepath, "r") as f:
            data = json.load(f)
            if not data:
                return None
            return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load cache from {filepath}: {e}")
        return None

async def process_service_item(item, tech_analyst, pricing_analyst, synthesizer, csp_a, csp_b, semaphore):
    async with semaphore:
        service_a = item["csp_a_service_name"]
        service_b = item.get("csp_b_service_name")

        if not service_b:
            logger.info(f"Skipping {service_a} (no match in {csp_b})")
            return None

        service_pair_id = f"{service_a}_vs_{service_b}"
        logger.info(f"Processing: {service_pair_id}")

        # Technical Analysis
        tech_file = f"data/technical_{service_pair_id}.json"
        tech_data = get_cached_data(tech_file)
        if not tech_data:
            tech_data = await tech_analyst.perform_analysis(csp_a, csp_b, item)
            if not tech_data:
                logger.warning(f"Technical analysis failed for {service_pair_id}")
                return None
            tech_data["service_pair_id"] = service_pair_id
            with open(tech_file, "w") as f:
                json.dump(tech_data, f, indent=2)
        else:
            logger.info(f"Using cached technical data for {service_pair_id}")

        # Pricing Analysis
        pricing_file = f"data/pricing_{service_pair_id}.json"
        pricing_data = get_cached_data(pricing_file)
        if not pricing_data:
            pricing_data = await pricing_analyst.perform_analysis(csp_a, csp_b, item)
            if not pricing_data:
                logger.warning(f"Pricing analysis failed for {service_pair_id}")
                return None
            pricing_data["service_pair_id"] = service_pair_id
            with open(pricing_file, "w") as f:
                json.dump(pricing_data, f, indent=2)
        else:
            logger.info(f"Using cached pricing data for {service_pair_id}")

        # Synthesis
        result_file = f"data/result_{service_pair_id}.json"
        result_json = get_cached_data(result_file)
        if not result_json:
            result_json = await synthesizer.synthesize(service_pair_id, tech_data, pricing_data)
            if not result_json:
                logger.warning(f"Synthesis failed for {service_pair_id}")
                return None
            with open(result_file, "w") as f:
                json.dump(result_json, f, indent=2)
        else:
            logger.info(f"Using cached result for {service_pair_id}")

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

    service_map_file = f"data/service_map_{csp_a}_{csp_b}.json"
    service_map = get_cached_data(service_map_file)

    if not service_map:
        service_map = await mapper.discover_services(csp_a, csp_b)
        # Save Service Map
        with open(service_map_file, "w") as f:
            json.dump(service_map, f, indent=2)
    else:
        logger.info(f"Using cached service map for {csp_a} vs {csp_b}")

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

    # --- Phase 5: Management Summary ---
    # Group results by domain
    services_by_domain = {}
    for item in final_results:
        domain = item["map"].get("domain", "Uncategorized")
        if domain not in services_by_domain:
            services_by_domain[domain] = []
        services_by_domain[domain].append(item["result"]["synthesis"])

    # Generate management summary for each domain
    management_summaries = {}
    summary_tasks = []

    for domain, synthesis_results in services_by_domain.items():
        summary_tasks.append(
            (domain, synthesizer.summarize_by_domain(domain, synthesis_results))
        )

    summary_results = await asyncio.gather(*[task for _, task in summary_tasks])

    for (domain, _), summary in zip(summary_tasks, summary_results):
        if summary:
            management_summaries[domain] = summary
        else:
            logger.warning(f"Management summary failed for domain {domain}")


    # --- Phase 5b: Overarching Summary ---
    overarching_summary = await synthesizer.summarize_overall(management_summaries)
    if not overarching_summary:
        logger.warning("Overarching summary generation failed.")

    # --- Phase 6: Visualization ---
    visualizer = DashboardGenerator()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_html = f"public/{csp_a}_{csp_b}_{timestamp}.html"

    visualizer.generate_dashboard(
        csp_a,
        csp_b,
        final_results,
        items,
        management_summaries,
        overarching_summary,
        output_html,
    )

    logger.info("Pipeline completed successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
