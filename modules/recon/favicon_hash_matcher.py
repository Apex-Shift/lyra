import base64
import mmh3
from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Favicon Murmur3 Hash Calculator",
        "description": "Télécharge la Favicon d'un site web, calcule son hash Murmur3 pour les recherches inversées sur Shodan/Censys (Bypass CDN/Cloudflare).",
        "author": "Lyra Core Dev Team",
        "category": "recon"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["TARGET_URL"] = Option("", required=True, description="URL du site cible ou du fichier favicon (ex: https://target.com/favicon.ico)")

    async def run(self) -> Dict[str, Any]:
        target_url = self.options["TARGET_URL"].value.rstrip("/")
        if not target_url.endswith(".ico") and not target_url.endswith(".png"):
            target_url = f"{target_url}/favicon.ico"
        if not target_url.startswith("http"):
            target_url = f"https://{target_url}"

        print(f"[*] Téléchargement et calcul du hash Murmur3 de la Favicon : {target_url}...")
        client = self.core.network_director.get_authenticated_client()

        try:
            async with client as session:
                resp = await session.get(target_url, follow_redirects=True)
                if resp.status_code != 200:
                    return {"status": "error", "message": f"Impossible d'obtenir la favicon (HTTP {resp.status_code})"}

                favicon_bytes = resp.content
                # Encodage base64 standard avec saut de ligne RFC 2045 tous les 76 caractères
                b64_content = base64.encodebytes(favicon_bytes)
                fav_hash = mmh3.hash(b64_content)

                shodan_query = f"http.favicon.hash:{fav_hash}"
                censys_query = f"services.http.response.favicons.shodan_hash: {fav_hash}"

                print(f"[+] Hash Murmur3 généré : {fav_hash}")
                print(f"[+] Requete Shodan : {shodan_query}")

                # Ingestion dans le graphe de session
                node_id = f"favicon_{fav_hash}"
                await self.core.context.add_entity(node_id, "Favicon_Hash", str(fav_hash), {
                    "shodan_dork": shodan_query,
                    "censys_dork": censys_query
                })

                return {
                    "target_url": target_url,
                    "murmur3_hash": fav_hash,
                    "shodan_query": shodan_query,
                    "censys_query": censys_query
                }
        except Exception as e:
            return {"status": "error", "message": f"Échec de l'opération : {e}"}