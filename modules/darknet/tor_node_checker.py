from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Tor Exit Node Identifier",
        "description": "Interroge la liste officielle des relais Onion pour déterminer si une adresse IP est un nœud de sortie (Tor Exit Node).",
        "author": "Lyra Core Dev Team",
        "category": "darknet"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["IP_ADDRESS"] = Option("", required=True, description="Adresse IPv4 à analyser")

    async def run(self) -> Dict[str, Any]:
        ip = self.options["IP_ADDRESS"].value.strip()
        print(f"[*] Vérification de l'adresse IP auprès du réseau Tor : {ip}...")

        url = "https://check.torproject.org/exit-addresses"
        client = self.core.network_director.get_authenticated_client()

        try:
            async with client as session:
                resp = await session.get(url)
                is_tor = ip in resp.text

                node_id = f"ip_{ip}"
                await self.core.context.add_entity(node_id, "IP_Address", ip, {"is_tor_exit_node": is_tor})

                if is_tor:
                    print(f"[!] ATTENTION : L'IP {ip} est un nœud de sortie Tor ACTIF !")
                else:
                    print(f"[+] L'IP {ip} n'apparaît pas dans la liste des relais de sortie Tor actuels.")

                return {"ip": ip, "is_tor_exit_node": is_tor}

        except Exception as e:
            return {"status": "error", "message": f"Échec de connexion : {e}"}