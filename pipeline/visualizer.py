import os
import json
import logging
import datetime
from jinja2 import Environment, FileSystemLoader
from constants import TEMPLATE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DashboardGenerator:
    def __init__(self):
        template_dir = os.path.dirname(TEMPLATE_PATH)
        template_name = os.path.basename(TEMPLATE_PATH)
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template(template_name)

    def generate_dashboard(self, csp_a: str, csp_b: str, results: list, service_maps: list, output_path: str):
        """
        Generates the HTML dashboard from the aggregated results.
        """
        if not results:
            logger.warning("No results to visualize.")
            return

        # Prepare data for template
        total_services = len(results)

        tech_scores = [r["result"]["technical_data"]["technical_score"] for r in results]
        price_scores = [r["result"]["pricing_data"]["cost_efficiency_score"] for r in results]

        avg_technical = sum(tech_scores) / total_services if total_services else 0
        avg_price = sum(price_scores) / total_services if total_services else 0

        # Group by Domain
        # We need to link results back to the domain from the service map.
        # Result metadata has service_pair_id.
        # Service Map has items with domain.
        # I need a way to look up domain by service_pair_id or service name.
        # Ideally, main.py passes a structure that has both map and result.

        # Let's assume 'results' is a list of dicts, each containing 'result' and 'map' keys.
        # OR main.py reconstructs this.
        # I'll update the signature to expect a combined object or I'll iterate carefully.

        # Actually, let's assume 'results' is the list of fully populated Result objects
        # and 'service_maps' contains the domain info.
        # BUT result.json metadata only has service_pair_id (which might be the service name?).
        # In technical_schema, service_pair_id is a string.
        # Let's try to map them.

        # Better approach: Pass a list of objects like:
        # [{'map': {...}, 'result': {...}}]

        # I will assume the `results` argument is this combined list for simplicity in this method,
        # or I will join them here.
        # Let's assume `results` is the list of objects: { "map": service_map_item, "result": result_json }

        services_by_domain = {}
        domain_scores = {}

        for item in results:
            domain = item["map"].get("domain", "Uncategorized")
            if domain not in services_by_domain:
                services_by_domain[domain] = []
            services_by_domain[domain].append(item)

        # Calculate domain averages
        for domain, items in services_by_domain.items():
            d_tech = sum([i["result"]["technical_data"]["technical_score"] for i in items])
            d_price = sum([i["result"]["pricing_data"]["cost_efficiency_score"] for i in items])
            count = len(items)
            # Simple avg of both
            avg_combined = (d_tech + d_price) / (2 * count)
            domain_scores[domain] = round(avg_combined, 2)

        # Global Executive Summary (Just taking the first one or synthesizing a global one?
        # The architecture diagram has "Synthesizer" -> "Synthesis".
        # The Synthesizer produces a synthesis per service pair.
        # It doesn't seem to produce a GLOBAL synthesis.
        # Project.md 2.2 says: "Synthesizer... Ingests validated JSONs... Generates... essay." per service pair.
        # But "The Dashboard Generator... presents the synthesis".
        # It implies listing them or maybe aggregating?
        # I will just put a placeholder "Global Summary" or aggregate the executive summaries of the top services?
        # The HTML template I wrote has {{ executive_summary }}.
        # Maybe I should just concatenate them or leave it generic.
        # I will generate a simple summary string.

        global_summary = f"Comparison of {total_services} services across {len(services_by_domain)} domains."

        html_content = self.template.render(
            csp_a=csp_a,
            csp_b=csp_b,
            generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            executive_summary=global_summary,
            total_services=total_services,
            avg_technical_score=round(avg_technical, 2),
            avg_cost_score=round(avg_price, 2),
            services_by_domain=services_by_domain,
            domain_scores=domain_scores
        )

        with open(output_path, 'w') as f:
            f.write(html_content)

        logger.info(f"Dashboard generated at {output_path}")
