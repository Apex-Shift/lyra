import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Pastebin Leak & Secret Analyzer",
        "description": "Scanne les dépôts publics récents sur Pastebin à la recherche de fuites de mots de passe, tokens et clés API ciblés.",
        "author": "Lyra Core Dev Team",
        "category": "leak"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["KEYWORD"] = Option("", required=True, description="Mot-clé ou domaine à rechercher (ex: @target.com ou api_key)")

    async def run(self) -> Dict[str, Any]:
        keyword = self.options["KEYWORD"].value.lower()
        print(f"[*] Inspection des fuites récentes contenant le terme : {keyword}...")

        client = self.core.network_director.get_authenticated_client()
        matched_pastes: List[Dict[str, str]] = []

        try:
            async with client as session:
                # Lecture de la page archive récente de Pastebin
                resp = await session.get("https://pastebin.com/archive", follow_redirects=True)
                soup = BeautifulSoup(resp.text, "html.parser")

                # Extraction des liens de pastes
                paste_links = [a["href"] for a in soup.find_all("a") if a.get("href", "").startswith("/") and len(a.get("href", "")) == 9]

                for link in paste_links[:10]:  # Scan des 10 plus récents
                    raw_url = f"https://pastebin.com/raw{link}"
                    try:
                        p_resp = await session.get(raw_url)
                        if keyword in p_resp.text.lower():
                            matched_pastes.append({"paste_id": link.strip("/"), "url": f"https://pastebin.com{link}"})
                            
                            node_id = f"pastebin_{link.strip('/')}"
                            await self.core.context.add_entity(node_id, "Paste_Leak", f"https://pastebin.com{link}")
                    except Exception:
                        continue

        except Exception as e:
            return {"status": "error", "message": f"Erreur de communication : {e}"}

        print(f"[+] {len(matched_pastes)} fuite(s) contenant '{keyword}' trouvée(s).")
        return {"keyword": keyword, "matches": matched_pastes}