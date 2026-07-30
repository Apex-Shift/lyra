from typing import Any, Dict, List
import dns.resolver
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Subdomain Takeover Detector",
        "description": "Scanne la résolution CNAME de sous-domaines pour identifier les pointeurs vers des services cloud abandonnés (GitHub Pages, Heroku, AWS S3).",
        "author": "Lyra Core Dev Team",
        "category": "osint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["TARGET_DOMAIN"] = Option("", required=True, description="Domaine ou sous-domaine cible (ex: sub.example.com)")

    async def run(self) -> Dict[str, Any]:
        target = self.options["TARGET_DOMAIN"].value.strip().lower()
        print(f"[*] Analyse DNS & CNAME pour la recherche de Takeover sur : {target}...")

        # Signatures de services cloud vulnérables lorsque l'enregistrement pointe vers une ressource supprimée
        dangling_signatures = {
            "github.io": "GitHub Pages",
            "herokuapp.com": "Heroku",
            "s3.amazonaws.com": "AWS S3 Bucket",
            "azurewebsites.net": "Azure Web App",
            "wordpress.com": "WordPress.com"
        }

        vulnerabilities: List[Dict[str, str]] = []

        try:
            answers = dns.resolver.resolve(target, 'CNAME')
            for rdata in answers:
                cname_target = str(rdata.target).rstrip('.')
                print(f"[+] CNAME trouvé : {target} -> {cname_target}")

                for sig_domain, service in dangling_signatures.items():
                    if sig_domain in cname_target:
                        vulnerabilities.append({
                            "subdomain": target,
                            "cname": cname_target,
                            "service": service
                        })

                        # Ingestion dans le graphe d'enquête
                        node_id = f"takeover_{target}"
                        await self.core.context.add_entity(node_id, "Vulnerable_CNAME", cname_target, {
                            "subdomain": target,
                            "service": service
                        })

        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            print("[-] Aucun enregistrement CNAME trouvé.")
        except Exception as e:
            return {"status": "error", "message": f"Erreur de résolution DNS : {e}"}

        return {
            "target": target,
            "vulnerabilities": vulnerabilities
        }