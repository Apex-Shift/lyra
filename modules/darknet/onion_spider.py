from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Tor Onion Stealth Spider",
        "description": "Inspecte et extrait en toute sécurité le contenu d'un site Web Tor .onion via le navigateur Playwright Stealth.",
        "author": "Lyra Core Dev Team",
        "category": "darknet"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["ONION_URL"] = Option("", required=True, description="Adresse .onion du forum/marché cible")

    async def run(self) -> Dict[str, Any]:
        onion_url = self.options["ONION_URL"].value
        if not onion_url.startswith("http"):
            onion_url = f"http://{onion_url}"

        print(f"[*] Tentative de connexion sécurisée au réseau Tor pour : {onion_url}...")
        
        # Bascule temporaire en mode Tor
        self.core.network_director.tor_enabled = True

        page = None
        try:
            # Obtention de la page via le moteur Playwright
            from core.browser_director import BrowserDirector
            browser_director = BrowserDirector(self.core.network_director)
            page = await browser_director.get_stealth_page()

            # Navigation vers l'adresse Onion avec timeout étendu
            await page.goto(onion_url, timeout=90000, wait_until="domcontentloaded")
            title = await page.title()
            
            # Extraction rapide des liens internes
            links = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")
            onion_links = list(set([l for l in links if ".onion" in l]))

            print(f"[+] Connexion réussie ! Titre de la page : {title}")
            print(f"[+] {len(onion_links)} lien(s) .onion interne(s) détecté(s).")

            # Mémorisation de l'entité
            target_node = f"onion_{onion_url}"
            await self.core.context.add_entity(target_node, "Onion_Service", onion_url, {"title": title})

            await browser_director.close()

            return {
                "status": "success",
                "onion_url": onion_url,
                "title": title,
                "internal_onion_links_count": len(onion_links),
                "sample_links": onion_links[:10]
            }

        except Exception as e:
            if page and page.context and page.context.browser:
                await page.context.browser.close()
            return {"status": "error", "message": f"Échec d'accès au circuit Tor : {e}"}