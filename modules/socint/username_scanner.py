import asyncio
import re
from typing import Any, Dict, List
from core.base_module import BaseModule, Option

# Liste de cibles rapides et fiables pour garantir zero crash API
TARGET_SITES = [
    {"name": "GitHub", "url": "https://github.com/{}", "check": "status", "code": 200},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{}/about.json", "check": "json_key", "key": "data"},
    {"name": "DockerHub", "url": "https://hub.docker.com/v2/users/{}", "check": "status", "code": 200},
    {"name": "GitLab", "url": "https://gitlab.com/api/v4/users?username={}", "check": "json_list"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{}", "check": "no_string", "string": "The specified profile could not be found"},
    {"name": "Pinterest", "url": "https://www.pinterest.com/{}/", "check": "status", "code": 200},
    {"name": "Dev.to", "url": "https://dev.to/{}", "check": "status", "code": 200},
    {"name": "Medium", "url": "https://medium.com/@{}", "check": "status", "code": 200},
    {"name": "Vimeo", "url": "https://vimeo.com/{}", "check": "status", "code": 200},
    {"name": "SoundCloud", "url": "https://soundcloud.com/{}", "check": "status", "code": 200},
    {"name": "Keybase", "url": "https://keybase.io/{}", "check": "status", "code": 200},
    {"name": "About.me", "url": "https://about.me/{}", "check": "status", "code": 200},
]

class Module(BaseModule):
    meta = {
        "name": "High-Speed Username Scanner",
        "description": "Fast SOCINT username lookup module.",
        "author": "Lyra Core Dev Team",
        "category": "socint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["USERNAME"] = Option("", required=True, description="Target username to search")

    async def _check_site(self, session, sem, site: Dict[str, Any], username: str) -> Dict[str, str] | None:
        url = site["url"].format(username)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with sem:
            try:
                # Timeout ultra strict (2.5s) pour empêcher le timed out de l'API Lyra
                resp = await session.get(url, headers=headers, follow_redirects=True, timeout=2.5)
                
                check_type = site.get("check")
                found = False

                if check_type == "status":
                    found = (resp.status_code == site.get("code", 200))
                elif check_type == "no_string":
                    found = (resp.status_code == 200) and (site["string"] not in resp.text)
                elif check_type == "json_key":
                    if resp.status_code == 200:
                        data = resp.json()
                        found = site["key"] in data
                elif check_type == "json_list":
                    if resp.status_code == 200:
                        data = resp.json()
                        found = isinstance(data, list) and len(data) > 0

                if found:
                    return {"platform": site["name"], "url": url}

            except Exception:
                return None

        return None

    async def run(self) -> Dict[str, Any]:
        username = self.options["USERNAME"].value.strip()
        if not username:
            return {"status": "error", "message": "No username provided"}

        # Récupération du client HTTP de Lyra
        client = self.core.network_director.get_authenticated_client()
        matches: List[Dict[str, str]] = []

        # Sémaphore limité pour ne pas saturer la boucle asyncio
        sem = asyncio.Semaphore(15)

        try:
            async with client as session:
                tasks = [self._check_site(session, sem, site, username) for site in TARGET_SITES]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for res in results:
                    if isinstance(res, dict) and res:
                        matches.append(res)
                        
                        # Injection dans le graphe/contexte Lyra si dispo
                        try:
                            target_id = f"user_{username}"
                            plat_id = f"profile_{res['platform']}_{username}"
                            await self.core.context.add_entity(target_id, "Username", username)
                            await self.core.context.add_entity(plat_id, "SocialProfile", res["url"])
                            await self.core.context.add_pivot(target_id, plat_id, "has_account_on", self.meta["name"])
                        except Exception:
                            pass

        except Exception as e:
            return {"status": "error", "message": str(e), "matches": []}

        return {
            "status": "success",
            "username": username,
            "count": len(matches),
            "matches": matches
        }