import json
import logging
from config import Config
from constants import MODEL_ANALYSIS, PROMPT_CONFIG_PATH, SOVEREIGNTY_SCHEMA_PATH
from pipeline.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOV_CONTROLS_DESC = """
SOV-01: Rechtlicher Sitz und Eigentümerstruktur
Kriterium: Der Cloud-Anbieter (CSP) muss seinen Hauptsitz und die tatsächliche Geschäftsleitung innerhalb der Europäischen Union (EU) oder des EWR haben. Das Stammkapital und die Stimmrechte müssen mehrheitlich (>50 %) von natürlichen oder juristischen Personen mit Sitz in der EU/EWR gehalten werden. Es muss gesellschaftsrechtlich sichergestellt sein, dass keine effektive Beherrschung durch Entitäten aus Drittstaaten möglich ist.
Zusatzhinweis: Joint Ventures sind zulässig, sofern der europäische Partner die operative Kontrolle und ein Vetorecht bei sicherheitsrelevanten Entscheidungen besitzt.

SOV-02: Datenlokation und Gerichtsstand
Kriterium: Alle Kundendaten, Metadaten, Authentifizierungsdaten und Backups müssen ausschließlich auf Servern innerhalb der EU/EWR gespeichert und verarbeitet werden. Der vertraglich vereinbarte Gerichtsstand und das anwendbare Recht müssen ausschließlich dem eines EU/EWR-Mitgliedstaates entsprechen.
Zusatzhinweis: Ein Datentransfer in Drittstaaten ist technisch zu unterbinden. Ausnahmen bedürfen der expliziten Initiierung durch den Kunden.

SOV-03: Schutz vor extraterritorialem Zugriff
Kriterium: Der CSP muss garantieren, dass er keinen Gesetzen oder Anordnungen von Drittstaaten unterliegt, die eine Herausgabe von Daten erzwingen könnten (z. B. FISA, US CLOUD Act), oder er muss rechtliche und technische Maßnahmen ergreifen, die einen solchen Zugriff effektiv verhindern. Anfragen ausländischer Behörden sind abzuweisen, sofern kein Rechtshilfeabkommen (MLAT) besteht.
Zusatzhinweis: Der CSP muss eine Transparenzbericht-Pflicht erfüllen und alle Zugriffsversuche von Drittstaaten dokumentieren.

SOV-04: Operative Betriebsführung
Kriterium: Der Betrieb, die Administration und die Wartung der Cloud-Infrastruktur dürfen ausschließlich durch Personal erfolgen, das im EU/EWR-Raum ansässig ist. Fernzugriffe (Remote Access) für Supportzwecke aus Drittstaaten sind technisch zu unterbinden ("Europäischer Admin-Schild").
Zusatzhinweis: "Follow-the-Sun"-Supportmodelle sind nur innerhalb der EU/EWR zulässig.

SOV-05: Kryptografische Hoheit und Schlüsselverwaltung
Kriterium: Der CSP muss Verfahren bereitstellen, die dem Kunden die alleinige Kontrolle über die Verschlüsselungsschlüssel ermöglichen (Bring Your Own Key / Hold Your Own Key). Die Schlüsselverwaltungssysteme (HSM) müssen in der EU/EWR betrieben werden. Der CSP darf technisch keinen Zugriff auf Klartextdaten oder Schlüsselmaterial haben.
Zusatzhinweis: Dies gilt für Daten im Ruhezustand (At Rest), während der Übertragung (In Transit) und während der Nutzung (In Use, z.B. durch Confidential Computing).

SOV-06: Unabhängigkeit der Lieferkette (Subdienstleister)
Kriterium: Der CSP muss sicherstellen, dass alle wesentlichen Unterauftragnehmer, die Zugriff auf Kundendaten oder Kerninfrastruktur haben, die Anforderungen SOV-01 bis SOV-05 ebenfalls erfüllen.
Zusatzhinweis: Kritische Kernprozesse dürfen nicht an Subunternehmer ausgelagert werden, die extraterritorialem Recht unterliegen.

SOV-07: Technische Transparenz und Auditierbarkeit (Code-Review)
Kriterium: Bei Einsatz von Software-Komponenten oder Plattform-Technologien, deren geistiges Eigentum bei Herstellern aus Drittstaaten liegt, muss eine vertraglich gesicherte Einsichtnahme in den Quellcode gewährleistet sein. Diese muss durch den CSP oder eine akkreditierte europäische Prüfstelle erfolgen, um Backdoors auszuschließen.
Zusatzhinweis: Dies betrifft insbesondere Hypervisor, IAM und Krypto-Module.

SOV-08: Update- und Patch-Souveränität
Kriterium: Der CSP muss die vollständige Kontrolle über den Software-Lebenszyklus haben. Automatische Updates durch Technologiegeber aus Drittstaaten sind technisch zu blockieren. Updates dürfen erst nach Prüfung und Freigabe durch den europäischen Betreiber eingespielt werden.
Zusatzhinweis: Der Betrieb muss auch bei Einstellung des Supports oder Sanktionen durch den Technologiegeber für einen definierten Migrationszeitraum gewährleistet sein (Sanktionsresilienz).

SOV-09: Erweiterte Sicherheitsüberprüfung des Personals
Kriterium: Personal mit administrativen privilegierten Zugriffsrechten auf Kerninfrastruktur oder Kundendaten muss einer erweiterten behördlichen Sicherheitsüberprüfung unterzogen werden (vergleichbar SÜG Ü2/Geheim oder europäisches Äquivalent).
Zusatzhinweis: Einfache polizeiliche Führungszeugnisse sind für diese Rollen nicht ausreichend.

SOV-10: Ausschluss technischer Fernabschaltung (Killswitch)
Kriterium: Der Einsatz von Software oder Hardware mit integrierten Mechanismen zur ferngesteuerten Deaktivierung, Funktionseinschränkung oder Lizenzsperrung (Killswitch) durch den Hersteller ist unzulässig. Der Betrieb der Cloud-Plattform muss auch bei dauerhafter Unterbrechung der Verbindung zu den Lizenzservern oder Management-Schnittstellen des Technologiegebers uneingeschränkt möglich sein.
Zusatzhinweis: Die Unabhängigkeit von externen Lizenz-Servern ("Phone Home"-Zwang) ist technisch nachzuweisen. Vertragliche Zusicherungen allein genügen nicht.
"""

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
                {"control_id": "SOV-01", "control_name": "Rechtlicher Sitz und Eigentümerstruktur", "score": 8, "reasoning": f"<p>{csp} has a strong European presence with local subsidiaries, but ultimate ownership may be international.</p>"},
                {"control_id": "SOV-02", "control_name": "Datenlokation und Gerichtsstand", "score": 10, "reasoning": f"<p>{csp} offers regions strictly within the EU with EU-based legal entities.</p>"},
                {"control_id": "SOV-03", "control_name": "Schutz vor extraterritorialem Zugriff", "score": 5, "reasoning": f"<p>{csp} implements technical measures, but is still subject to some international legal pressures.</p>"},
                {"control_id": "SOV-04", "control_name": "Operative Betriebsführung", "score": 7, "reasoning": f"<p>Operations are largely EU-based for specific 'sovereign' regions.</p>"},
                {"control_id": "SOV-05", "control_name": "Kryptografische Hoheit und Schlüsselverwaltung", "score": 9, "reasoning": f"<p>{csp} provides advanced HYOK/BYOK options with EU-resident HSMs.</p>"},
                {"control_id": "SOV-06", "control_name": "Unabhängigkeit der Lieferkette (Subdienstleister)", "score": 6, "reasoning": f"<p>Supply chain is being audited, with increasing focus on EU sub-processors.</p>"},
                {"control_id": "SOV-07", "control_name": "Technische Transparenz und Auditierbarkeit", "score": 4, "reasoning": f"<p>Source code access is limited but audited by accredited third parties.</p>"},
                {"control_id": "SOV-08", "control_name": "Update- und Patch-Souveränität", "score": 5, "reasoning": f"<p>Update processes allow for some delay and local review for sovereign clouds.</p>"},
                {"control_id": "SOV-09", "control_name": "Erweiterte Sicherheitsüberprüfung des Personals", "score": 8, "reasoning": f"<p>Staff in sensitive roles undergo rigorous background checks.</p>"},
                {"control_id": "SOV-10", "control_name": "Ausschluss technischer Fernabschaltung (Killswitch)", "score": 7, "reasoning": f"<p>Disconnection resilience is part of the architecture for sovereign offerings.</p>"}
            ]
            return {"csp": csp, "controls": controls}

        prompt_config = self.prompts["sovereignty_prompt"]
        system_instruction = prompt_config["system_instruction"]
        user_content = prompt_config["user_template"].format(
            csp=csp,
            control_descriptions=SOV_CONTROLS_DESC
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
            return response

        except Exception as e:
            logger.error(f"Error performing sovereignty analysis for {csp}: {e}")
            return None
