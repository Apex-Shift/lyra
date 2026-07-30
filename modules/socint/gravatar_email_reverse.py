import hashlib
from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Gravatar Reverse Email Identifier",
        "description": "Génère le hash MD5/SHA256 d'une adresse email pour vérifier l'existence d'un profil Gravatar et extraire l'avatar et les données publiques.",
        "author": "Lyra Core Dev Team",
        "category": "socint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["EMAIL"] = Option("", required=True, description="Adresse email cible à analyser")

    async def run(self) -> Dict[str, Any]:
        email = self.options["EMAIL"].value.lower().strip()
        email_hash = hashlib.md5(email.encode("utf-8")).hexdigest()

        print(f"[*] Génération du hash MD5 pour : {email} ({email_hash})...")
        json_profile_url = f"https://www.gravatar.com/{email_hash}.json"
        avatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"

        client = self.core.network_director.get_authenticated_client()

        try:
            async with client as session:
                resp = await session.get(json_profile_url)
                if resp.status_code == 200:
                    profile_data = resp.json().get("entry", [{}])[0]
                    username = profile_data.get("preferredUsername", "N/A")
                    display_name = profile_data.get("displayName", "N/A")

                    print(f"[+] Profil Gravatar DÉTECTÉ ! Nom : {display_name} | Pseudo : {username}")

                    node_id = f"gravatar_{email_hash}"
                    await self.core.context.add_entity(node_id, "Gravatar_Profile", json_profile_url, {
                        "email": email,
                        "display_name": display_name,
                        "username": username
                    })

                    return {
                        "status": "found",
                        "email": email,
                        "hash": email_hash,
                        "displayName": display_name,
                        "username": username,
                        "avatar_url": avatar_url
                    }
                else:
                    print("[-] Aucun profil Gravatar associé à cet e-mail.")
                    return {"status": "not_found", "email": email, "hash": email_hash}

        except Exception as e:
            return {"status": "error", "message": f"Erreur de recherche : {e}"}