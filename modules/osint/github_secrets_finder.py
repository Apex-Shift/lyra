import re
from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "GitHub Public Code Secret Scanner",
        "description": "Recherche dans les dépôts publics GitHub des fuites de tokens, clés AWS, clés d'API et identifiants associés à un nom d'organisation ou domaine.",
        "author": "Lyra Core Dev Team",
        "category": "osint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["QUERY"] = Option("", required=True, description="Terme de recherche OSINT (ex: target.com API_KEY ou targetcorp AWS_SECRET)")

    async def run(self) -> Dict[str, Any]:
        query = self.options["QUERY"].value.strip()
        print(f"[*] Interrogation de l'API Search GitHub pour : {query}...")

        client = self.core.network_director.get_authenticated_client()
        search_url = f"https://api.github.com/search/code?q={query}"
        
        leaks_found: List[Dict[str, str]] = []

        try:
            async with client as session:
                resp = await session.get(search_url, headers={"Accept": "application/vnd.github.v3+json"})
                
                if resp.status_code == 403:
                    return {"status": "error", "message": "Limite d'API GitHub atteinte (Rate Limit). Réessayez ultérieurement."}
                
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])

                    for item in items[:10]:
                        file_url = item.get("html_url", "")
                        repo_name = item.get("repository", {}).get("full_name", "")
                        
                        leaks_found.append({
                            "repository": repo_name,
                            "file_url": file_url
                        })

                        node_id = f"github_leak_{hash(file_url)}"
                        await self.core.context.add_entity(node_id, "GitHub_Code_Leak", file_url, {
                            "repository": repo_name
                        })

                    print(f"[+] {len(leaks_found)} résultat(s) potentiellement sensible(s) extrait(s) de GitHub.")
                    return {"query": query, "results_count": data.get("total_count", 0), "leaks": leaks_found}

        except Exception as e:
            return {"status": "error", "message": f"Échec de la recherche GitHub : {e}"}

        return {"status": "error", "message": "Impossible de traiter la requête."}