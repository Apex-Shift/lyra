import re
from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Router & Web Server Access Log Analyzer",
        "description": "Analyse les journaux d'accès Nginx, Apache ou pare-feu/routeurs à la recherche de scans Web (SQLi, XSS, Path Traversal).",
        "author": "Lyra Core Dev Team",
        "category": "network"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["LOG_FILE"] = Option("", required=True, description="Chemin vers le fichier access.log ou log du routeur")

    async def run(self) -> Dict[str, Any]:
        log_path = self.options["LOG_FILE"].value
        print(f"[*] Analyse du journal réseau / serveur : {log_path}...")

        attack_patterns = {
            "SQL Injection": [r"UNION\s+SELECT", r"OR\s+1=1", r"SLEEP\(", r"BENCHMARK\("],
            "Path Traversal / LFI": [r"\.\./\.\./", r"/etc/passwd", r"c:\\boot.ini"],
            "Command Injection": [r";\s*cat\s+", r"\|\s*nc\s+", r"`whoami`"],
            "XSS": [r"<script>", r"javascript:", r"onerror="]
        }

        detected_attacks: List[Dict[str, str]] = []

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    for attack_type, patterns in attack_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                detected_attacks.append({
                                    "category": attack_type,
                                    "line": line.strip()[:200]
                                })

            node_id = f"netlog_{hash(log_path)}"
            await self.core.context.add_entity(node_id, "Network_Log_Analysis", log_path, {
                "total_attacks_detected": len(detected_attacks)
            })

            print(f"[!] Alertes de sécurité : {len(detected_attacks)} tentative(s) d'attaque identifiée(s).")
            return {
                "file": log_path,
                "total_alerts": len(detected_attacks),
                "sample_alerts": detected_attacks[:10]
            }

        except Exception as e:
            return {"status": "error", "message": f"Échec du traitement du fichier : {e}"}