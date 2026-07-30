from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Furtive Social Profile Scraper",
        "description": "Utilise le navigateur Headless Stealth pour inspecter et extraire discrètement les données publiques d'un profil social.",
        "author": "Lyra Core Dev Team",
        "category": "socint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["PROFILE_URL"] = Option("", required=True, description="URL du profil réseau social cible")

    async def run(self) -> Dict[str, Any]:
        profile_url = self.options["PROFILE_URL"].value
        print(f"[*] Lancement de la navigation furtive vers : {profile_url}...")

        from core.browser_director import BrowserDirector
        browser_director = BrowserDirector(self.core.network_director)

        try:
            page = await browser_director.get_stealth_page()
            await page.goto(profile_url, timeout=30000, wait_until="domcontentloaded")

            # Extraction du titre de la page et des métadonnées OpenGraph
            title = await page.title()
            description = ""

            meta_desc = await page.query_selector("meta[property='og:description']")
            if meta_desc:
                description = await meta_desc.get_attribute("content") or ""

            await browser_director.close()

            # Enregistrement dans le graphe de session
            profile_id = f"social_{profile_url}"
            await self.core.context.add_entity(
                entity_id=profile_id,
                entity_type="Social_Profile",
                value=profile_url,
                metadata={"title": title, "description": description}
            )

            print(f"[+] Scraping réussi ! Titre : {title}")
            return {
                "profile_url": profile_url,
                "page_title": title,
                "meta_description": description,
                "status": "success"
            }

        except Exception as e:
            await browser_director.close()
            return {"status": "error", "message": f"Échec du scraping furtif : {e}"}