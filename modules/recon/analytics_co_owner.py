import re
from typing import Any, Dict, Set
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Analytics Co-Owner Network Finder",
        "description": "Extrait les identifiants AdSense/Analytics pour découvrir tous les domaines appartenant à la même entité.",
        "author": "Lyra Core Dev Team",
        "category": "recon"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["TARGET_URL"] = Option("", required=True, description="URL complète du site cible (ex: https://target.com)")

    async def run(self) -> Dict[str, Any]:
        target_url = self.options["TARGET_URL"].value
        if not target_url.startswith("http"):
            target_url = f"https://{target_url}"

        print(f"[*] Analyse des empreintes de tracking sur : {target_url}...")
        client = self.core.network_director.get_authenticated_client()

        tracking_ids: Set[str] = set()
        try:
            async with client as session:
                resp = await session.get(target_url, follow_redirects=True)
                html_content = resp.text

                # Expressions régulières pour cibler les identifiants uniques
                ga_legacy = re.findall(r"UA-\d+-\d+", html_content)
                ga_v4 = re.findall(r"G-[A-Z0-9]+", html_content)
                adsense = re.findall(r"pub-\d+", html_content)

                tracking_ids.update(ga_legacy)
                tracking_ids.update(ga_v4)
                tracking_ids.update(adsense)

        except Exception as e:
            return {"status": "error", "message": f"Échec d'analyse réseau : {e}"}

        found_list = list(tracking_ids)
        print(f"[+] Identifiants uniques extraits : {found_list}")

        # Enregistrement dans le graphe relationnel de session
        target_node_id = f"domain_{target_url}"
        await self.core.context.add_entity(target_node_id, "Domain", target_url)

        pivoted_domains = []
        for track_id in found_list:
            track_node_id = f"track_{track_id}"
            await self.core.context.add_entity(track_node_id, "Tracking_ID", track_id)
            await self.core.context.add_pivot(target_node_id, track_node_id, "uses_tracking_id", self.meta["name"])

        return {
            "target": target_url,
            "tracking_identifiers": found_list,
            "pivot_count": len(found_list)
        }