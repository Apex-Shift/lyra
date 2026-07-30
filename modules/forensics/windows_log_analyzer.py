import json
from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Windows EVTX & Sysmon Log Analyzer",
        "description": "Analyse les journaux d'événements Windows (EVTX au format JSON/text) pour repérer les tentatives d'escalade de privilèges, échecs d'authentification (4625) et exécutions suspectes (Sysmon Event ID 1).",
        "author": "Lyra Core Dev Team",
        "category": "forensics"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["LOG_FILE"] = Option("", required=True, description="Chemin vers le fichier de log Windows (JSON ou format texte exporté)")

    async def run(self) -> Dict[str, Any]:
        log_path = self.options["LOG_FILE"].value
        print(f"[*] Analyse forensique du journal d'événements Windows : {log_path}...")

        suspicious_events: List[Dict[str, Any]] = []
        failed_logins = 0

        # Event IDs critiques
        # 4625: Échec d'authentification
        # 4624: Connexion réussie
        # 4672: Privilèges d'administrateur attribués
        # 1 (Sysmon): Création de processus
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            for line in lines:
                # Analyse rapide des Event IDs
                if "4625" in line:
                    failed_logins += 1
                
                if any(sec in line.lower() for sec in ["mimikatz", "powershell -enc", "cmd.exe /c", "vssadmin delete"]):
                    suspicious_events.append({
                        "type": "SUSPICIOUS_COMMAND",
                        "raw_entry": line.strip()[:150]
                    })

            # Ingestion dans le graphe
            node_id = f"winlog_{hash(log_path)}"
            await self.core.context.add_entity(node_id, "Windows_Log_Analysis", log_path, {
                "failed_logins_count": failed_logins,
                "suspicious_commands_found": len(suspicious_events)
            })

            print(f"[+] Analyse terminée : {failed_logins} échecs de connexion (ID 4625), {len(suspicious_events)} commandes suspectes trouvées.")
            return {
                "file": log_path,
                "failed_logins_count": failed_logins,
                "suspicious_events": suspicious_events
            }

        except Exception as e:
            return {"status": "error", "message": f"Échec de lecture des logs : {e}"}