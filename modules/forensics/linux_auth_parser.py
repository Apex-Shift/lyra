import re
from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Linux Auth & Sudo Log Inspector",
        "description": "Inspecte les fichiers /var/log/auth.log ou /var/log/secure pour extraire les attaques par force brute SSH et les commandes sudo suspectes.",
        "author": "Lyra Core Dev Team",
        "category": "forensics"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["LOG_FILE"] = Option("/var/log/auth.log", required=True, description="Chemin vers le fichier de log (ex: /var/log/auth.log)")

    async def run(self) -> Dict[str, Any]:
        log_path = self.options["LOG_FILE"].value
        print(f"[*] Inspection des accès Linux sur : {log_path}...")

        failed_ssh_ips: Dict[str, int] = {}
        sudo_commands: List[str] = []

        # RegEx pour SSH et Sudo
        ssh_failed_pattern = re.compile(r"Failed password for (?:invalid user )?(\w+) from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        sudo_pattern = re.compile(r"COMMAND=(.*)")

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Détection Brute Force SSH
                    ssh_match = ssh_failed_pattern.search(line)
                    if ssh_match:
                        ip = ssh_match.group(2)
                        failed_ssh_ips[ip] = failed_ssh_ips.get(ip, 0) + 1

                    # Détection d'exécutions Sudo
                    if "COMMAND=" in line:
                        sudo_match = sudo_pattern.search(line)
                        if sudo_match:
                            sudo_commands.append(sudo_match.group(1))

            # Trier les IP d'attaquants les plus agressifs
            top_attackers = sorted(failed_ssh_ips.items(), key=lambda x: x[1], reverse=True)[:5]

            node_id = f"linuxlog_{hash(log_path)}"
            await self.core.context.add_entity(node_id, "Linux_Auth_Analysis", log_path, {
                "unique_attacker_ips": len(failed_ssh_ips),
                "sudo_execution_count": len(sudo_commands)
            })

            print(f"[+] {len(failed_ssh_ips)} IP(s) attaquantes détectées. Top attaquant : {top_attackers[0] if top_attackers else 'Aucun'}")
            return {
                "file": log_path,
                "top_bruteforce_ips": top_attackers,
                "recent_sudo_commands": sudo_commands[-10:]  # 10 dernières commandes Sudo
            }

        except Exception as e:
            return {"status": "error", "message": f"Erreur lors du traitement : {e}"}