import json
import logging
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, SOVEREIGNTY_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOV_CONTROLS = {
    "SOV-01": {
        "name": "Legal Seat and Ownership Structure",
        "description": "Criterion: The Cloud Service Provider (CSP) must have its head office and effective management within the European Union (EU) or the EEA. Majority (>50%) of share capital and voting rights must be held by natural or legal persons based in the EU/EEA. It must be legally ensured that no effective control by entities from third countries is possible.\nAdditional Note: Joint ventures are permitted as long as the European partner has operational control and veto rights for security-relevant decisions."
    },
    "SOV-02": {
        "name": "Data Location and Jurisdiction",
        "description": "Criterion: All customer data, metadata, authentication data, and backups must be stored and processed exclusively on servers within the EU/EEA. The contractually agreed jurisdiction and applicable law must exclusively be that of an EU/EEA member state.\nAdditional Note: Data transfer to third countries must be technically prevented. Exceptions require explicit initiation by the customer."
    },
    "SOV-03": {
        "name": "Protection Against Extraterritorial Access",
        "description": "Criterion: The CSP must guarantee that it is not subject to laws or orders from third countries that could compel the disclosure of data (e.g., FISA, US CLOUD Act), or it must take legal and technical measures that effectively prevent such access. Requests from foreign authorities must be rejected unless a Mutual Legal Assistance Treaty (MLAT) exists.\nAdditional Note: The CSP must fulfill a transparency reporting obligation and document all access attempts from third countries."
    },
    "SOV-04": {
        "name": "Operational Management",
        "description": "Criterion: Operation, administration, and maintenance of the cloud infrastructure must be performed exclusively by personnel residing in the EU/EEA. Remote access for support purposes from third countries must be technically prevented ('European Admin Shield').\nAdditional Note: 'Follow-the-Sun' support models are only permitted within the EU/EEA."
    },
    "SOV-05": {
        "name": "Cryptographic Sovereignty and Key Management",
        "description": "Criterion: The CSP must provide procedures that allow the customer sole control over encryption keys (Bring Your Own Key / Hold Your Own Key). Key management systems (HSM) must be operated in the EU/EEA. The CSP must technically have no access to plaintext data or key material.\nAdditional Note: This applies to data at rest, in transit, and in use (e.g., through Confidential Computing)."
    },
    "SOV-06": {
        "name": "Supply Chain Independence (Sub-processors)",
        "description": "Criterion: The CSP must ensure that all essential subcontractors with access to customer data or core infrastructure also meet the requirements SOV-01 to SOV-05.\nAdditional Note: Critical core processes must not be outsourced to subcontractors subject to extraterritorial law."
    },
    "SOV-07": {
        "name": "Technical Transparency and Auditability (Code Review)",
        "description": "Criterion: When using software components or platform technologies whose intellectual property belongs to manufacturers from third countries, contractually secured inspection of the source code must be guaranteed. This must be carried out by the CSP or an accredited European auditing body to exclude backdoors.\nAdditional Note: This particularly affects hypervisors, IAM, and crypto modules."
    },
    "SOV-08": {
        "name": "Update and Patch Sovereignty",
        "description": "Criterion: The CSP must have full control over the software lifecycle. Automatic updates by technology providers from third countries must be technically blocked. Updates may only be installed after review and approval by the European operator.\nAdditional Note: Operation must be guaranteed for a defined migration period even if support is discontinued or sanctions are imposed by the technology provider (sanction resilience)."
    },
    "SOV-09": {
        "name": "Enhanced Security Clearance for Personnel",
        "description": "Criterion: Personnel with administrative privileged access rights to core infrastructure or customer data must undergo enhanced official security clearance (comparable to SÜG Ü2/Secret or European equivalent).\nAdditional Note: Simple police clearance certificates are not sufficient for these roles."
    },
    "SOV-10": {
        "name": "Exclusion of Technical Remote Shutdown (Killswitch)",
        "description": "Criterion: The use of software or hardware with integrated mechanisms for remote deactivation, functional restriction, or license blocking (killswitch) by the manufacturer is inadmissible. The operation of the cloud platform must be fully possible even if the connection to the license servers or management interfaces of the technology provider is permanently interrupted.\nAdditional Note: Independence from external license servers ('Phone Home' compulsion) must be technically proven. Contractual assurances alone are not enough."
    }
}

class SovereigntyAnalyst:
    def __init__(self):
        self.client = GeminiClient()
        self.model_name = MODEL_ANALYSIS
        self._load_assets()

    def _load_assets(self):
        with open(PROMPT_CONFIG_PATH, 'r') as f:
            self.prompts = json.load(f)

        with open(SOVEREIGNTY_SCHEMA_PATH, 'r') as f:
            self.schema = json.load(f)

    async def perform_analysis(self, csp: str) -> dict:
        if Config.TEST_MODE:
            logger.info(f"TEST_MODE enabled for SovereigntyAnalyst. Returning mock data for {csp}")
            # Generate mock data that matches the schema
            controls = [
                {"control_id": "SOV-01", "control_name": "Legal Seat and Ownership Structure", "score": 8, "reasoning": f"<p>{csp} has a strong European presence with local subsidiaries, but ultimate ownership may be international.</p>"},
                {"control_id": "SOV-02", "control_name": "Data Location and Jurisdiction", "score": 10, "reasoning": f"<p>{csp} offers regions strictly within the EU with EU-based legal entities.</p>"},
                {"control_id": "SOV-03", "control_name": "Protection Against Extraterritorial Access", "score": 5, "reasoning": f"<p>{csp} implements technical measures, but is still subject to some international legal pressures.</p>"},
                {"control_id": "SOV-04", "control_name": "Operational Management", "score": 7, "reasoning": f"<p>Operations are largely EU-based for specific 'sovereign' regions.</p>"},
                {"control_id": "SOV-05", "control_name": "Cryptographic Sovereignty and Key Management", "score": 9, "reasoning": f"<p>{csp} provides advanced HYOK/BYOK options with EU-resident HSMs.</p>"},
                {"control_id": "SOV-06", "control_name": "Supply Chain Independence (Sub-processors)", "score": 6, "reasoning": f"<p>Supply chain is being audited, with increasing focus on EU sub-processors.</p>"},
                {"control_id": "SOV-07", "control_name": "Technical Transparency and Auditability", "score": 4, "reasoning": f"<p>Source code access is limited but audited by accredited third parties.</p>"},
                {"control_id": "SOV-08", "control_name": "Update and Patch Sovereignty", "score": 5, "reasoning": f"<p>Update processes allow for some delay and local review for sovereign clouds.</p>"},
                {"control_id": "SOV-09", "control_name": "Enhanced Security Clearance for Personnel", "score": 8, "reasoning": f"<p>Staff in sensitive roles undergo rigorous background checks.</p>"},
                {"control_id": "SOV-10", "control_name": "Exclusion of Technical Remote Shutdown (Killswitch)", "score": 7, "reasoning": f"<p>Disconnection resilience is part of the architecture for sovereign offerings.</p>"}
            ]
            # Inject descriptions into mock data
            for ctrl in controls:
                ctrl["control_description"] = SOV_CONTROLS.get(ctrl["control_id"], {}).get("description", "")
            return {"csp": csp, "controls": controls}

        # Prepare control descriptions string for the prompt
        descriptions_list = []
        for cid, info in SOV_CONTROLS.items():
            descriptions_list.append(f"{cid}: {info['name']}\n{info['description']}")
        control_descriptions_str = "\n\n".join(descriptions_list)

        prompt_config = self.prompts["sovereignty_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(
            csp=csp,
            control_descriptions=control_descriptions_str
        )

        try:
            response = await self.client.generate_content(
                model_name=self.model_name,
                user_content=user_content,
                system_instruction=system_instruction,
                schema=self.schema,
                enable_grounding=True
            )
            if response is None:
                logger.error(f"Received None response from GeminiClient for sovereignty analysis of {csp}")
                return None

            # Inject descriptions and names into response for consistency
            for ctrl in response.get("controls", []):
                control_info = SOV_CONTROLS.get(ctrl["control_id"], {})
                if control_info:
                    ctrl["control_name"] = control_info["name"]
                    ctrl["control_description"] = control_info["description"]

            return response

        except Exception as e:
            logger.error(f"Error performing sovereignty analysis for {csp}: {e}")
            return None
