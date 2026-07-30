from typing import Any, Dict, List
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Cloud S3 Bucket Enumerator",
        "description": "Génère et teste des permutations de noms de buckets AWS S3 pour identifier des espaces de stockage cloud mal configurés.",
        "author": "Lyra Core Dev Team",
        "category": "recon"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["COMPANY_NAME"] = Option("", required=True, description="Nom de l'organisation ou marque (ex: targetcorp)")

    async def run(self) -> Dict[str, Any]:
        company = self.options["COMPANY_NAME"].value.lower().strip()
        print(f"[*] Génération des permutations et scan des Buckets AWS S3 pour : {company}...")

        suffixes = ["", "-assets", "-data", "-backup", "-public", "-dev", "-staging", "-media", "-files", "-prod"]
        buckets_to_test = [f"{company}{s}" for s in suffixes]

        found_buckets: List[Dict[str, Any]] = []
        client = self.core.network_director.get_authenticated_client()

        async with client as session:
            for b_name in buckets_to_test:
                url = f"https://{b_name}.s3.amazonaws.com"
                try:
                    resp = await session.get(url)
                    status = resp.status_code

                    # 200 = Public Listable, 403 = Protected (Exists), 404 = Does Not Exist
                    if status in [200, 403]:
                        access_type = "PUBLIC_READ" if status == 200 else "PROTECTED_EXISTS"
                        found_buckets.append({"bucket": b_name, "url": url, "status": status, "access": access_type})

                        # Ajout au graphe d'enquête
                        node_id = f"s3_{b_name}"
                        await self.core.context.add_entity(node_id, "S3_Bucket", url, {"access": access_type})
                except Exception:
                    continue

        print(f"[+] {len(found_buckets)} Bucket(s) S3 identifié(s).")
        return {"company": company, "detected_buckets": found_buckets}