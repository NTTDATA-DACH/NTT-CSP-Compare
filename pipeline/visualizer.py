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

    def generate_dashboard(
        self,
        csp_a: str,
        csp_b: str,
        results: list,
        service_maps: list,
        management_summaries: dict,
        overarching_summary: dict,
        output_path: str,
    ):
        """
        Generates the HTML dashboard from the aggregated results.
        """
        missing_services_list = [
            item for item in service_maps if not item.get("csp_b_service_name")
        ]

        if not results and not missing_services_list:
            logger.warning("No results or missing services to visualize.")
            return

        # Prepare data for template
        total_compared = len(results)
        total_services_csp_a = len(service_maps)

        tech_scores = (
            [r["result"]["technical_data"]["technical_score"] for r in results]
            if results
            else []
        )
        price_scores = (
            [r["result"]["pricing_data"]["cost_efficiency_score"] for r in results]
            if results
            else []
        )

        avg_technical = sum(tech_scores) / total_compared if total_compared else 0
        avg_price = sum(price_scores) / total_compared if total_compared else 0

        # Group by Domain
        services_by_domain = {}
        domain_scores = {}
        domain_scores_tech = {}
        domain_scores_cost = {}

        for item in results:
            domain = item["map"].get("domain", "Uncategorized")
            if domain not in services_by_domain:
                services_by_domain[domain] = []
            services_by_domain[domain].append(item)

        # Calculate domain averages for table display and chart
        for domain, items in services_by_domain.items():
            count = len(items)
            d_tech = sum(
                [i["result"]["technical_data"]["technical_score"] for i in items]
            )
            d_price = sum(
                [i["result"]["pricing_data"]["cost_efficiency_score"] for i in items]
            )

            avg_combined = (d_tech + d_price) / (2 * count) if count > 0 else 0
            domain_scores[domain] = round(avg_combined, 2)

            domain_scores_tech[domain] = round(d_tech / count, 2) if count > 0 else 0
            domain_scores_cost[domain] = round(d_price / count, 2) if count > 0 else 0

        # Prepare data for Chart.js spider web graph
        chart_labels = list(services_by_domain.keys())
        chart_tech_data = [domain_scores_tech[d] for d in chart_labels]
        chart_cost_data = [domain_scores_cost[d] for d in chart_labels]

        domain_scores_chart_data = {
            "labels": json.dumps(chart_labels),
            "datasets": [
                {
                    "label": f"Technical Score ({csp_b} vs {csp_a})",
                    "data": json.dumps(chart_tech_data),
                    "fill": True,
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderColor": "rgb(54, 162, 235)",
                    "pointBackgroundColor": "rgb(54, 162, 235)",
                },
                {
                    "label": f"Cost Efficiency ({csp_b} vs {csp_a})",
                    "data": json.dumps(chart_cost_data),
                    "fill": True,
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderColor": "rgb(255, 99, 132)",
                    "pointBackgroundColor": "rgb(255, 99, 132)",
                },
            ],
        }

        # Render final HTML
        html_content = self.template.render(
            csp_a=csp_a,
            csp_b=csp_b,
            generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overarching_summary=overarching_summary,
            management_summaries=management_summaries,
            total_services=total_services_csp_a,
            total_compared=total_compared,
            avg_technical_score=round(avg_technical, 2),
            avg_cost_score=round(avg_price, 2),
            services_by_domain=services_by_domain,
            domain_scores=domain_scores,
            domain_scores_chart_data=domain_scores_chart_data,
            missing_services=missing_services_list,
        )

        with open(output_path, 'w') as f:
            f.write(html_content)

        logger.info(f"Dashboard generated at {output_path}")
