import re
from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Darknet PGP Key & Identity Extractor",
        "description": "Scanne les pages d'un service cachés Tor (.onion) ou document texte pour trouver et extraire les clés publiques PGP et identités associées.",
        "author": "Lyra Core Dev Team",
        "category": "osint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["TARGET_URL"] = Option("", required=True, description="URL du site .onion ou fichier texte à analyser")

    async def run(self) -> Dict[str, Any]:
        target_url = self.options["TARGET_URL"].value.strip()
        print(f"[*] Extraction de clés PGP sur la ressource Darknet : {target_url}...")

        client = self.core.network_director.get_authenticated_client()
        pgp_blocks: List[str] = []
        user_ids: List[str] = []

        try:
            async with client as session:
                resp = await session.get(target_url, follow_redirects=True)
                content = resp.text

                # Expression régulière pour détecter les blocs de clés PGP publiques
                pgp_pattern = re.compile(r"-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]*?-----END PGP PUBLIC KEY BLOCK-----")
                matches = pgp_pattern.findall(content)

                # Detection d'identités PGP (ex: User ID: Name <email@domain.com>)
                uid_pattern = re.compile(r"([a-zA-Z0-9._%+-]+ <[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}>)")
                uids = uid_pattern.findall(content)

                for match in matches:
                    pgp_blocks.append(match[:100] + "... [TRONQUÉ]")

                for uid in uids:
                    user_ids.append(uid)

                node_id = f"darknet_pgp_{hash(target_url)}"
                await self.core.context.add_entity(node_id, "Darknet_PGP_Analysis", target_url, {
                    "pgp_keys_count": len(matches),
                    "identities_found": len(user_ids)
                })

                print(f"[+] {len(matches)} bloc(s) de clés PGP et {len(user_ids)} identité(s) repérée(s).")
                return {
                    "target_url": target_url,
                    "keys_found_count": len(matches),
                    "identities": list(set(user_ids)),
                    "pgp_samples": pgp_blocks
                }

        except Exception as e:
            return {"status": "error", "message": f"Échec de l'accès à la ressource : {e}"}