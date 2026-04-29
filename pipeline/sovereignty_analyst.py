import json
import logging
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, SOVEREIGNTY_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOV_CONTROLS = {
    "SOV-1-01": {
        "name": "Jurisdiction",
        "description": "SOV-1-01-C1 Criterion\nThe cloud service provider MUST operate under EU jurisdiction, with contract governance and dispute resolution.\nSOV-1-01-C2 Criterion\nThe cloud service provider MUST operate under German jurisdiction, with contract governance and dispute resolution.\nSOV-1-01-SI Supplementary information\nIf restrictions are imposed by cloud service customers for Germany, they should be justified, and it should be ensured that their implementation, for example, in procurement procedures, is legally permissible on the basis of reasons such as public safety."
    },
    "SOV-1-02": {
        "name": "Registered Office",
        "description": "SOV-1-02-C1 Criterion\nThe cloud service provider MUST have a registered head office in the EU.\nSOV-1-02-C2 Criterion\nThe cloud service provider MUST have a registered head office in Germany.\nSOV-1-02-SI Supplementary information\nIf the cloud service provider uses a subcontractor for the provision of services, such as operations, that subcontractor MUST also meet the criteria. If restrictions are imposed by cloud service customers for EU or Germany, they should be justified, and it should be ensured that their implementation, for example, in procurement procedures, is legally permissible on the basis of reasons such as public safety."
    },
    "SOV-1-03": {
        "name": "CSP Effective Control",
        "description": "SOV-1-03-C1 Criterion\nThe cloud service provider MUST be effectively controlled by one or more EU corporations. The cloud service provider MUST ensure that effective controls are transparent to cloud service customers.\nSOV-1-03-C2 Criterion\nThe cloud service provider MUST be under the effective control of one or more German undertakings. The cloud service provider MUST ensure that effective controls are transparent to cloud service customers.\nSOV-1-03-SI Supplementary information\nEffective control in this context means the possibility to exert direct or indirect influence, or determine the key strategic, financial, or operational decisions from non-EU undertakings. If restrictions are imposed by cloud service customers for EU or Germany, they should be justified, and it should be ensured that their implementation, for example, in procurement procedures, is legally permissible on the basis of reasons such as public safety."
    },
    "SOV-1-04": {
        "name": "CSP Control Change",
        "description": "SOV-1-04-C Criterion\nThe cloud service provider MUST inform cloud service customers 90 days in advance of any actual changes affecting the cloud service provider's control that could undermine or affect the C3A controls associated with the cloud service, including significant changes to ownership, shareholding, or governance relationships of the cloud service provider."
    },
    "SOV-2-01": {
        "name": "Extraterritorial Exposure",
        "description": "SOV-2-01-C Criterion\nThe cloud service provider MUST identify, at least once a year, any non-EU law relating directly to the provided cloud services that have cross-border implications for the availability of cloud services and the confidentiality and integrity of customer created data. They MUST also carry out a structured risk assessment to evaluate the risks arising from these laws."
    },
    "SOV-2-02": {
        "name": "Audit Rights",
        "description": "SOV-2-02-C1 Criterion\nThe cloud service provider MUST document procedures that allow the relevant federal or national cybersecurity authority to verify compliance with the C3A criteria by an audit. The responsible authority is the one in the country where the data center is located.\nSOV-2-02-C2 Criterion\nThe cloud service provider MUST document procedures that allow the German federal administration to verify compliance with the C3A criteria by an audit.\nSOV-2-02-SI Supplementary information\nThe audit rights may be derived from a contract or law that explicitly reserves the right for the federal or national authority to conduct audits. If possible, the authority tries to make use of existing audits (e.g., BSI C5, SOC 2 Type 2) before carrying out an audit. Any audit shall be conducted in accordance with the cloud service provider's strict security and confidentiality protocols, including defined notice periods, to protect the data of other tenants and the integrity of the data centre. While costs are a commercial matter, the right to audit is a regulatory mandate. Fees shall not be so high as to effectively deny this right."
    },
    "SOV-2-03": {
        "name": "State of Defense Takeover",
        "description": "SOV-2-03-C1 Criterion\nIf an EU member state declares a state of defense, the cloud service provider MUST enable the EU member state to take over the capabilities required to operate the cloud, including the necessary physical assets and personnel, within the framework of legal possibilities.\nSOV-2-03-C2 Criterion\nIf Germany declares a state of defense, the cloud service provider MUST enable the German federal administration to take over the capabilities required to operate the cloud, including the necessary material assets and personnel, within the framework of legal possibilities.\nSOV-2-03-SI Supplementary information\nThis usually means that the cloud service provider has the documentation, source code and administration tools in a portable format so that a federal administration can use them."
    },
    "SOV-3-01": {
        "name": "Data Residence",
        "description": "SOV-3-01-C1 Criterion\nA cloud service customer MUST be able to check where their cloud service derived data, cloud service customer data, and account data are stored and processed.\nSOV-3-01-C2 Criterion\nThe cloud service provider MUST provide a service option where cloud service derived data and account data are exclusively stored and processed in the EU.\nSOV-3-01-C3 Criterion\nThe cloud service provider MUST provide a service option where cloud service customer data is exclusively stored and processed in the EU.\nSOV-3-01-C4 Criterion\nThe cloud service provider MUST provide a service option where cloud service customer data is exclusively stored and processed in Germany.\nSOV-3-01-C5 Criterion\nThe cloud service provider MUST provide a service option where cloud service provider data is exclusively stored and processed in the EU.\nSOV-3-01-SI Supplementary information\nIf a cloud service provider operates in other locations/regions in addition to the EU or Germany, the location/region of processing and storing MUST be clearly identifiable for the cloud service customer."
    },
    "SOV-3-02": {
        "name": "External Key Management",
        "description": "SOV-3-02-C Criterion\nThe cloud service provider MUST allow the integration of external encryption key management system for creating, managing, and storing encryption keys outside of the cloud service provider environment for the use of IaaS and PaaS, or provide functionally equivalent mechanisms that ensure the customer can only create, manage and store the encryption keys only outside of the cloud service provider environment.\nSOV-3-02-AC Additional criterion\nThe cloud service provider MUST allow the integration of external key management systems for creating, managing and storing keys outside of the cloud environment also for SaaS, or provide functionally equivalent mechanisms that ensure the customer can only create, manage and store the encryption keys outside of the cloud service provider environment.\nSOV-3-02-SI Supplementary information\nThe integration of external key management systems for IaaS and PaaS is widely implemented and commonly standardized. For SaaS solutions, external encryption key management systems are less common; therefore, cloud service providers should support external encryption key management capabilities for SaaS where technically feasible and appropriate to the service architecture. If this criterion is only fulfilled for some SaaS, the cloud service provider MUST provide a list of these services to the cloud services customer."
    },
    "SOV-3-03": {
        "name": "External Identity Provider",
        "description": "SOV-3-03-C Criterion\nThe cloud service provider MUST support standards-based integration of external identity providers for authentication and access management for the cloud service.\nSOV-3-03-AC1 Additional criterion\nThe integration of an external Identity Provider MUST be implemented via open, non-proprietary standards.\nSOV-3-03-AC2 Additional criterion\nThe provider MUST support a stateless authentication model that does not mandate the creation and copies of accounts within the provider’s directory.\nSOV-3-03-AC3 Additional criterion\nAuthorization MUST be controllable via dynamic claims and attributes issued directly by the customer's external identity provider."
    },
    "SOV-3-04": {
        "name": "Logging and Monitoring",
        "description": "SOV-3-04-C Criterion\nThe cloud service provider MUST provide customers with the capability to record, retain, and review logs of management and data access activities related to cloud service customer data. These logs MUST enable customers to identify when access occurred, the identity associated with the request, and the relevant operational context available through the service’s logging capabilities.\nSOV-3-04-AC1 Additional criterion\nThe logging service MUST ensure full data flow transparency by providing real-time access via standardized open-source APIs.\nSOV-3-04-AC2 Additional criterion\nThe service MUST support granular filtering."
    },
    "SOV-3-05": {
        "name": "Client-Side Encryption",
        "description": "SOV-3-05-C Criterion\nThe cloud service provider MUST enable client-side encryption of cloud service customer data. Whenever the cloud service customer data is transmitted, processed or stored inside the cloud environment, it MUST be encrypted with a private key that is only available to the cloud service customer outside of the cloud service provider environment.\nSOV-3-05-SI Supplementary information\nIf this criterion is only fulfilled for some cloud services, the cloud service provider MUST provide a list of these services to the cloud services customer."
    },
    "SOV-4-01": {
        "name": "Operating Personnel",
        "description": "SOV-4-01-C1 Criterion\nAll personnel who have logical or physical access to infrastructure used to operate the cloud service, as well as those who are responsible for customer support, and all persons who have management control of the cloud service provider MUST be EU citizens with EU as main residency.\nSOV-4-01-C2 Criterion\nAll personnel who have logical or physical access to infrastructure used to operate the cloud service, as well as those who are responsible for customer support, and all persons who have management control of the cloud service provider MUST be EU citizens with Germany as main residency.\nSOV-4-01-C3 Additional criterion\nThe operating personnel is part of an organization that MUST be a standalone European organization."
    },
    "SOV-4-02": {
        "name": "Remote Work",
        "description": "SOV-4-02-C1 Criterion\nThe cloud service provider MUST implement organizational and technical measures ensuring that administrative access to systems used to operate the cloud service is performed through access paths located within the EU. Administrative access originating from locations outside the EU MUST be technically restricted, except in narrowly defined and controlled exceptional scenarios that are subject to additional authorization and monitoring controls.\nSOV-4-02-C2 Criterion\nThe cloud service provider MUST implement organizational and technical measures ensuring that administrative access to systems used to operate the cloud service is performed through access paths located within the EU. Administrative access originating from locations outside Germany MUST be technically restricted, except in narrowly defined and controlled exceptional scenarios that are subject to additional authorization and monitoring controls."
    },
    "SOV-4-03": {
        "name": "Redundant connectivity providers",
        "description": "SOV-4-03-C Criterion\nThe cloud service provider MUST ensure redundant and independent connectivity for the delivery of the sovereign cloud service. In the event of a disruption of one connectivity provider, alternative connectivity providers MUST be able to maintain connectivity in accordance with the contractual service level agreements. At least one of the connectivity providers MUST be an EU based company.\nSOV-4-03-AC Additional criterion\nAt least one of the connectivity providers is not part of the corporate structure of the cloud service provider."
    },
    "SOV-4-04": {
        "name": "SOC",
        "description": "SOV-4-04-C1 Criterion\nThe cloud service provider MUST ensure that Security Operations Center (SOC) capabilities for the offered cloud services are established and operated within the EU. In the case of a disconnect (SOV-4-10), a standalone and equivalent SOC MUST be provided in the EU.\nSOV-4-04-C2 Criterion\nThe cloud service provider MUST ensure that Security Operations Center (SOC) capabilities for the offered cloud services are established and operated within Germany. In the case of a disconnect (SOV-4-10), a standalone and equivalent SOC MUST be provided in Germany."
    },
    "SOV-4-05": {
        "name": "Ingress Data Control",
        "description": "SOV-4-05-C Criterion\nAll software updates and operational data affecting the cloud service MUST be received, authorized and validated in a secured network area managed and controlled by the cloud service provider. The cloud service provider MUST verify and check updates for known vulnerabilities. Updates MUST include documentation satisfying the needs of the cloud service provider. The update process MUST be based on a controlled change management processes.\nSOV-4-05-AC1 Additional criterion\nThe cloud service provider MUST implement the secure network area (e.g. DMZ) on dedicated physical devices.\nSOV-4-05-AC2 Additional criterion\nThe cloud service provider MUST provide technical documentation how the criterion SOV-4-05-C is implemented to the responsible cybersecurity authority if requested, in accordance with applicable law and established supervisory, cooperation agreements or audit mechanisms. The responsible authority is the one in the country where the data center is located. Such information may be provided through appropriate confidentiality protections and secure disclosure procedures.\nSOV-4-05-SI Supplementary information\nA vulnerability is regarded as known, when it is listed in the European Union Vulnerability Database (EUVD) or in the Common Vulnerabilities and Exposures (CVE) Program from the National Institute of Standards and Technology (NIST)."
    },
    "SOV-4-06": {
        "name": "Update threat analysis",
        "description": "SOV-4-06-C Criterion\nWhen using third-party software under the cloud service provider’s responsibility, the cloud service provider MUST implement risk-based security analysis prior to deployment, including measures to detect and mitigate malicious code, viruses, spyware, and ransomware."
    },
    "SOV-4-07": {
        "name": "Data exchange monitoring",
        "description": "SOV-4-07-C Criterion\nAny cloud service derived data, cloud service customer data and account data exchanged between the cloud service provider and third parties MUST always be monitored, controlled and logged. In order to do so, the cloud service provider MUST establish a documented process. The documentation MUST be reviewed and updated regularly, at least once a year. The cloud service provider MUST document what kind of data is exchanged with third parties. This documentation MUST ensure that it is clear which data is flowing to which party and this can also be meaningfully aggregated. The cloud service provider MUST make this documentation available to the cloud service customer. It is acceptable that this is only made available to the customer if they have agreed to keep the information confidential and not publicly disclose it. The cloud service provider MUST clearly define the exchange format and document it as part of the data exchange documentation.\nSOV-4-07-SI Supplementary information\nIn the context of this requirement, a cloud service customer is not considered a third party. An associated company within the same group of companies is classified as a third party."
    },
    "SOV-4-08": {
        "name": "Data exchange gateways",
        "description": "SOV-4-08-C Criterion\nThe cloud service provider MUST document, define, and visualize (via a Data Flow Diagram) all data exchanges between the cloud service provider and third parties of cloud service derived data, cloud service customer data, and account data. The data exchanges MUST occur only via known gateways. The documentation MUST clearly identify data origins, destinations, transport protocols, data type and security mechanisms protecting these exchanges. The documentation MUST be reviewed and updated regularly, at least once a year. This documentation does not need to be published publicly.\nSOV-4-08-AC Additional criterion\nThe cloud service provider MUST provide the Data Flow Diagram to the responsible cybersecurity authority if requested, in accordance with applicable law and established supervisory, cooperation agreements or audit mechanisms. The responsible authority is the one in the country where the data center is located. Such information may be provided through appropriate confidentiality protections and secure disclosure procedures.\nSOV-4-08-SI Supplementary information\nIn the context of this requirement, a cloud service customer is not considered a third party. An associated company within the same group of companies is classified as a third party."
    },
    "SOV-4-09": {
        "name": "Disconnect",
        "description": "SOV-4-09-C Criterion\nThe cloud service provider MUST be able to disconnect all non-EU network-connections to the cloud without an impairment of the availability, integrity, authenticity and confidentiality of the cloud service. This includes all incoming updates and data exchanges with non-EU entities (including but not limited to: external heartbeat signals and global license validation servers) that are in the responsibility of the cloud service provider. The cloud service provider MUST establish and document a process, when and how a disconnect is executed. This process MUST be independent from non-EU entities. The cloud service provider MUST update this documentation regularly, at least once a year. The cloud service provider MUST conduct disconnection tests for ensuring the availability of all cloud services in case of a disconnection from the non-EU network-connections at least once a year. The cloud service provider MUST document these tests as part of the aforementioned documentations. The documentation MUST include, but is not limited to, the results of the performed test.\nSOV-4-09-AC Additional criterion\nThe cloud service provider MUST provide the documentation of the disconnect process and disconnection tests to the responsible cybersecurity authority if requested, in accordance with applicable law and established supervisory, cooperation agreements or audit mechanisms. Where relevant, the cloud service provider may provide supporting documentation. The responsible authority is the one in the country where the data center is located. Such information may be provided through appropriate confidentiality protections and secure disclosure procedures.\nSOV-4-09-SI Supplementary information\nIn the context of the disconnect requirement, network connections between the cloud service provider and cloud service customers are excluded from the scope of the disconnection capability."
    },
    "SOV-4-10": {
        "name": "Reconnect",
        "description": "SOV-4-10-C Criterion\nThe cloud service provider MUST be able to reestablish all non-EU-connections after a disconnect in accordance of criterion SOV-4-9-C (\"Disconnect\") has been performed and has a process to install updates if the cloud environment was disconnected for a maximum of 90 days. The process to install updates if the cloud environment was disconnected for at most 90 days MUST also be tested."
    },
    "SOV-5-01": {
        "name": "Software Dependencies",
        "description": "SOV-5-01-C Criterion\nThe cloud service provider MUST identify, for each cloud service, the software components used and their respective countries of origin. A list of the relevant software suppliers and their country or countries for each service, MUST be compiled and available on demand to cloud service customers. The identification of the software components should be based on a Software Bill of Materials (SBOM) (e.g. TR-03183-2) or achieve a comparable level of quality.\nSOV-5-01-AC Additional criterion\nThe cloud service provider MUST maintain a risk-based process for identifying and mitigating dependencies on external software suppliers relevant to the operation of the cloud service. Where critical dependencies are identified, the cloud service provider MUST implement appropriate mitigation strategies and maintain architectural flexibility that enables substitution of software components. If it is not technically and reasonably feasible, this information MUST be adequately provided to the cloud service customer.\nSOV-5-01-SI Supplementary information\nThe terms software components and software suppliers refer exclusively to software used by the cloud service provider to deliver the cloud service. Software deployed by customers or marketplace providers is excluded. Software components under widely used open-source licenses may be excluded from origin reporting where license terms restrict redistribution of such information. TR-03183 current version: https://www.bsi.bund.de/dok/TR-03183 . The quality of the SBOM should meet the requirements of the TR-03183 or use comparable alternatives. It is acceptable that this is only made available to the customer if he has agreed to keep the information confidential and not publicly disclose it."
    },
    "SOV-5-02": {
        "name": "Hardware Dependencies",
        "description": "SOV-5-02-C Criterion\nThe cloud service provider MUST maintain a documented inventory of the hardware components used to provide cloud services. A list of the relevant hardware suppliers and their country or countries MUST be compiled and available on demand to cloud service customers.\nSOV-5-02-AC Additional criterion\nThe cloud service provider MUST maintain a risk-based process for identifying and mitigating dependencies on hardware suppliers relevant to the operation of the cloud service. Where critical dependencies are identified, the cloud service provider MUST implement mitigation strategies and maintain architectural flexibility enabling substitution of hardware components. If it is not technically and operationally feasible, this information MUST be adequately provided to the cloud service customer.\nSOV-5-02-SI Supplementary information\nIt is acceptable that this is only made available to the customer if he has agreed to keep the information confidential and not publicly disclose it."
    },
    "SOV-5-03": {
        "name": "External Service Dependencies",
        "description": "SOV-5-03-C Criterion\nThe cloud service provider MUST maintain a documented inventory of used external cloud services that are necessary for the delivery of the cloud service. The list of information regarding the relevant external service providers and the country or countries of service provision or development MUST be made available to cloud service customers.\nSOV-5-03-AC Additional criterion\nThe cloud service provider MUST maintain a documented process for identifying and managing external service dependencies relevant to the delivery of the cloud service. Where critical dependencies are identified, the cloud service provider MUST implement mitigation strategies and maintain architectural flexibility enabling substitution of service dependencies. If it is not technically and operationally feasible, this information MUST be adequately provided to the cloud service customer.\nSOV-5-03-SI Supplementary information\nExternal services refer exclusively to services that are functionally required for the provision of the cloud service itself. In this context, external cloud services refer to services provided by third-party cloud providers that are integrated into the delivery of the primary cloud service but are operated and maintained by separate providers. It is acceptable that this is only made available to the customer if he has agreed to keep the information confidential and not publicly disclose it."
    },
    "SOV-5-04": {
        "name": "Export Restriction",
        "description": "SOV-5-04-C Criterion\nThe cloud service provider MUST maintain documented processes for identifying and mitigating risks related to export restrictions or supply chain disruptions affecting software, external services, and hardware used in the delivery of the cloud service. Where such restrictions may materially affect the operation of the cloud service, the cloud service provider MUST inform affected customers"
    },
    "SOV-5-05": {
        "name": "Capacity Management",
        "description": "SOV-5-05-C1 Criterion\nCapacity management MUST be performed in the EU in accordance with C5.\nSOV-5-05-C2 Criterion\nCapacity management MUST be performed in Germany in accordance with C5."
    },
    "SOV-6-01": {
        "name": "Source Code Availability",
        "description": "SOV-6-01-C Criterion\nThe cloud service provider MUST have a backup of the source code in the EU that is not older than 24 hours and contains at minimum 5 versions of the cloud services so that the operation of the cloud service is possible at any time without external dependencies. This includes all infrastructure-as-code build-scripts and deployment toolchains. The local source code backup MUST include a documentation that enables the cloud service provider to independently work with the source code and develop it further at any time without external dependencies."
    },
    "SOV-6-02": {
        "name": "Continuous Service Delivery",
        "description": "SOV-6-02-C Criterion\nIn the event of disconnection of third parties, the cloud service provider MUST maintain documented contingency strategies ensuring continued secure delivery of the cloud services. These strategies may include alternative software suppliers, internal remediation capabilities, or compensating security controls.\nSOV-6-02-AC Additional criterion\nIn the event of disruption or loss of an external software vendor, the cloud service provider MUST maintain the capability to remediate software vulnerabilities and implement necessary changes. The cloud provider MUST maintain specialized engineering talent and local build-environments necessary to compile, test, and deploy emergency security patches to the cloud services independently of third parties."
    },
    "SOV-6-03": {
        "name": "Software Development",
        "description": "SOV-6-03-C Criterion\nThe cloud service provider MUST ensure that authorised personnel have access to the software development tools and environments necessary to maintain and update the cloud services. The cloud service provider MUST also maintain documented contingency procedures for scenarios in which access to critical software development tools or development environment dependencies is disrupted, ensuring the continued ability to maintain and update the cloud services."
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
            controls = []
            for control_id, control_info in SOV_CONTROLS.items():
                controls.append({
                    "control_id": control_id,
                    "control_name": control_info["name"],
                    "score": 8,
                    "reasoning": f"<p>Mock reasoning for {control_id} for {csp}.</p>"
                })
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
