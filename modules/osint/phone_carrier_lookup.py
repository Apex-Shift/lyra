from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Phone Carrier & Number Intelligence",
        "description": "Analyse un numéro de téléphone international pour extraire l'opérateur attribué, le type de ligne (Mobile/VoIP/Fixe) et le pays d'origine.",
        "author": "Lyra Core Dev Team",
        "category": "osint"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["PHONE_NUMBER"] = Option("", required=True, description="Numéro au format international E.164 (ex: +33612345678)")

    async def run(self) -> Dict[str, Any]:
        phone = self.options["PHONE_NUMBER"].value.strip().replace(" ", "")
        print(f"[*] Analyse OSINT du numéro de téléphone : {phone}...")

        # Utilisation de l'API libre veriphone / numlookup public endpoint (fallback de démonstration)
        url = f"https://veriphone.now.sh/v2/verify?phone={phone}"
        client = self.core.network_director.get_authenticated_client()

        try:
            async with client as session:
                resp = await session.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    carrier = data.get("carrier", "Inconnu")
                    line_type = data.get("line_type", "Inconnu")
                    country = data.get("country", "Inconnu")
                    is_valid = data.get("phone_valid", False)

                    node_id = f"phone_{phone}"
                    await self.core.context.add_entity(node_id, "Phone_Number", phone, {
                        "carrier": carrier,
                        "line_type": line_type,
                        "country": country,
                        "valid": is_valid
                    })

                    print(f"[+] Résultat : Pays={country} | Opérateur={carrier} | Type={line_type}")
                    return {
                        "phone": phone,
                        "valid": is_valid,
                        "country": country,
                        "carrier": carrier,
                        "line_type": line_type
                    }
                else:
                    return {"status": "error", "message": "Impossible de joindre le service d'enrichissement Télécom."}

        except Exception as e:
            return {"status": "error", "message": f"Échec de la recherche : {e}"}