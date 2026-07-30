import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Telegram Public Channel Scraper",
        "description": "Inspecte les messages publics d'un canal ou groupe Telegram (t.me/s/channel) pour extraire les liens, adresses e-mails et mots-clés sans API.",
        "author": "Lyra Core Dev Team",
        "category": "osint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["CHANNEL_NAME"] = Option("", required=True, description="Nom d'utilisateur du canal Telegram (ex: durov ou nom_du_canal)")

    async def run(self) -> Dict[str, Any]:
        channel = self.options["CHANNEL_NAME"].value.strip().lstrip("@")
        target_url = f"https://t.me/s/{channel}"

        print(f"[*] Extraction OSINT du canal Telegram public : {target_url}...")
        client = self.core.network_director.get_authenticated_client()

        extracted_emails: List[str] = []
        extracted_links: List[str] = []

        try:
            async with client as session:
                resp = await session.get(target_url, follow_redirects=True)
                if resp.status_code != 200:
                    return {"status": "error", "message": f"Canal introuvable ou privé (HTTP {resp.status_code})"}

                soup = BeautifulSoup(resp.text, "html.parser")
                messages = soup.find_all("div", class_="tgme_widget_message_text")

                for msg in messages:
                    text = msg.get_text()
                    
                    # Extraction Regex d'emails
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                    extracted_emails.extend(emails)

                    # Extraction de liens externes
                    for a in msg.find_all("a", href=True):
                        href = a["href"]
                        if not href.startswith("https://t.me/"):
                            extracted_links.append(href)

                # Dédoublonner
                extracted_emails = list(set(extracted_emails))
                extracted_links = list(set(extracted_links))

                node_id = f"telegram_{channel}"
                await self.core.context.add_entity(node_id, "Telegram_Channel", target_url, {
                    "emails_found": len(extracted_emails),
                    "external_links_found": len(extracted_links)
                })

                print(f"[+] Analyse Telegram terminée : {len(extracted_emails)} e-mail(s) et {len(extracted_links)} lien(s) extrait(s).")
                return {
                    "channel": channel,
                    "emails": extracted_emails,
                    "external_links": extracted_links[:15]
                }

        except Exception as e:
            return {"status": "error", "message": f"Échec de l'analyse du canal : {e}"}