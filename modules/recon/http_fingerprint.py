import re
from typing import Any, Dict, List, Set
from bs4 import BeautifulSoup
from core.base_module import BaseModule, Option


# Matrice de signatures centralisée (CMS, Frameworks, Plugins & Analytics)
TECH_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "WordPress": {
        "headers": ["wp-super-cache", "x-pingback"],
        "meta": ["wordpress"],
        "html": ["wp-content", "wp-includes"],
        "js": ["wp-embed.min.js", "wp-includes/js"],
        "dirs": ["/wp-admin/"]
    },
    "Joomla": {
        "headers": [],
        "meta": ["joomla"],
        "html": ["/media/system/js/", "joomla!"],
        "js": ["/media/jui/js/"],
        "dirs": ["/administrator/"]
    },
    "Drupal": {
        "headers": ["x-drupal-cache", "x-generator"],
        "meta": ["drupal"],
        "html": ["drupal.settings", "sites/default/files"],
        "js": ["drupal.js"],
        "dirs": ["/admin/"]
    },
    "Shopify": {
        "headers": ["x-shopify-stage"],
        "meta": ["shopify"],
        "html": ["cdn.shopify.com"],
        "js": ["shopify_stats.js"],
        "dirs": []
    },
    "Elementor": {
        "headers": [],
        "meta": ["elementor"],
        "html": ["elementor-element", "elementor-widget"],
        "js": ["elementor/assets/js"],
        "dirs": []
    },
    "Yoast SEO": {
        "headers": [],
        "meta": ["yoast"],
        "html": ["yoast-schema-graph"],
        "js": [],
        "dirs": []
    },
    "WooCommerce": {
        "headers": [],
        "meta": [],
        "html": ["woocommerce-page", "woocommerce-no-js"],
        "js": ["woocommerce.min.js"],
        "dirs": []
    }
}


class Module(BaseModule):
    meta = {
        "name": "Advanced Tech Stack & CMS Fingerprinter",
        "description": "Détecte les CMS, plugins, bibliothèques JS et WAF via métadonnées, en-têtes HTTP, scripts et sondage d'arborescence.",
        "author": "Lyra Core Dev Team",
        "category": "recon"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["TARGET_URL"] = Option("", required=True, description="URL complète du site cible (ex: https://target.com)")
        self.options["PROBE_DIRS"] = Option(True, required=False, description="Activer le sondage furtif des répertoires d'administration")

    async def run(self) -> Dict[str, Any]:
        target_url = self.options["TARGET_URL"].value.rstrip('/')
        if not target_url.startswith("http"):
            target_url = f"https://{target_url}"

        probe_dirs = bool(self.options["PROBE_DIRS"].value)
        print(f"[*] Fingerprinting avancé de la pile technologique sur : {target_url}...")

        detected_techs: Dict[str, Set[str]] = {}
        client = self.core.network_director.get_authenticated_client()

        try:
            async with client as session:
                # 1. Requête principale et récupération du HTML & Headers
                resp = await session.get(target_url, follow_redirects=True)
                headers = {k.lower(): v.lower() for k, v in resp.headers.items()}
                html_raw = resp.text
                html_lower = html_raw.lower()
                soup = BeautifulSoup(html_raw, 'html.parser')

                # 2. Analyse des balises <meta generator> et équivalents
                generator_meta = soup.find('meta', attrs={'name': re.compile(r'generator', re.I)})
                if generator_meta and generator_meta.get('content'):
                    gen_val = generator_meta['content']
                    self._add_detection(detected_techs, "Generator Tag", gen_val)

                # 3. Empreintes dans les en-têtes HTTP
                if "server" in headers:
                    self._add_detection(detected_techs, "Web Server", resp.headers["Server"])
                if "x-powered-by" in headers:
                    self._add_detection(detected_techs, "Backend Framework", resp.headers["X-Powered-By"])
                
                # WAF / CDN Detection
                if "cf-ray" in headers or "cf-cache-status" in headers:
                    self._add_detection(detected_techs, "WAF/CDN", "Cloudflare")
                elif "x-akamai-transformed" in headers:
                    self._add_detection(detected_techs, "WAF/CDN", "Akamai")

                # 4. Extraction des liens <script src> et <link href>
                asset_urls: List[str] = []
                for tag in soup.find_all(['script', 'link'], src=True):
                    asset_urls.append(tag.get('src', '').lower())
                for tag in soup.find_all('link', href=True):
                    asset_urls.append(tag.get('href', '').lower())

                # 5. Matching contre la matrice des signatures (CMS & Plugins)
                for tech_name, sigs in TECH_SIGNATURES.items():
                    # Matching Headers
                    for h_sig in sigs["headers"]:
                        if any(h_sig in h for h in headers.keys()):
                            self._add_detection(detected_techs, "CMS/Plugin", f"{tech_name} (Header)")

                    # Matching Meta
                    for m_sig in sigs["meta"]:
                        if generator_meta and m_sig in generator_meta.get('content', '').lower():
                            self._add_detection(detected_techs, "CMS/Plugin", f"{tech_name} (Meta)")

                    # Matching HTML
                    for html_sig in sigs["html"]:
                        if html_sig in html_lower:
                            self._add_detection(detected_techs, "CMS/Plugin", f"{tech_name} (HTML)")

                    # Matching Script/CSS assets
                    for js_sig in sigs["js"]:
                        if any(js_sig in asset for asset in asset_urls):
                            self._add_detection(detected_techs, "CMS/Plugin", f"{tech_name} (JS/Asset)")

                # 6. Sondage de répertoires d'administration (Optionnel)
                if probe_dirs:
                    for tech_name, sigs in TECH_SIGNATURES.items():
                        for path in sigs["dirs"]:
                            probe_url = f"{target_url}{path}"
                            try:
                                p_resp = await session.head(probe_url, follow_redirects=True)
                                if p_resp.status_code in [200, 403]:
                                    self._add_detection(detected_techs, "CMS/Plugin", f"{tech_name} (Dir: {path})")
                            except Exception:
                                continue

        except Exception as e:
            return {"status": "error", "message": f"Échec de l'analyse : {e}"}

        # Conversion du dictionnaire pour le rapport final
        formatted_results = {k: list(v) for k, v in detected_techs.items()}

        # Enregistrement dans le graphe relationnel de session Lyra
        target_node = f"webapp_{target_url}"
        await self.core.context.add_entity(target_node, "Web_Application", target_url, {"technologies": formatted_results})

        print(f"[+] Analyse terminée. Catégories identifiées : {len(formatted_results)}")
        return {
            "target": target_url,
            "status": "success",
            "technologies": formatted_results
        }

    def _add_detection(self, store: Dict[str, Set[str]], category: str, item: str) -> None:
        if category not in store:
            store[category] = set()
        store[category].add(item)