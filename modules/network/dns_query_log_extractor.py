from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "DNS Query & Exfiltration Detector",
        "description": "Examine les journaux de requêtes DNS (Pi-hole, BIND9, Windows DNS) pour détecter l'exfiltration de données par tunnel DNS et le beaconing de botnets.",
        "author": "Lyra Core Dev Team",
        "category": "network"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["LOG_FILE"] = Option("", required=True, description="Chemin vers le journal de requêtes DNS")

    async def run(self) -> Dict[str, Any]:
        log_path = self.options["LOG_FILE"].value
        print(f"[*] Extraction et analyse du trafic DNS depuis : {log_path}...")

        suspicious_domains: List[str] = []
        domain_counts: Dict[str, int] = {}

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parts = line.split()
                    for part in parts:
                        if "." in part and len(part) > 4:
                            domain = part.strip("();,").lower()
                            
                            # Détection de requêtes excessivement longues (Signe typique de DNS Tunneling / Exfiltration)
                            if len(domain) > 50 and domain not in suspicious_domains:
                                suspicious_domains.append(domain)

                            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Domaines les plus sollicités (Beaconing potentiel)
            top_queried = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            node_id = f"dnslog_{hash(log_path)}"
            await self.core.context.add_entity(node_id, "DNS_Log_Analysis", log_path, {
                "suspicious_tunneling_domains": len(suspicious_domains)
            })

            print(f"[+] {len(suspicious_domains)} domaine(s) suspect(s) de tunneling détecté(s).")
            return {
                "file": log_path,
                "suspicious_tunneling_domains": suspicious_domains[:10],
                "top_queried_domains": top_queried
            }

        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la lecture du fichier DNS : {e}"}