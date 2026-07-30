import re
from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Blockchain Wallet Linker",
        "description": "Inspecte et extrait les adresses crypto (BTC/ETH) pour la traçabilité des transactions.",
        "author": "Lyra Core Dev Team",
        "category": "leak"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["WALLET_ADDRESS"] = Option("", required=True, description="Adresse de portefeuille crypto (BTC/ETH)")

    async def run(self) -> Dict[str, Any]:
        wallet = self.options["WALLET_ADDRESS"].value.strip()
        print(f"[*] Analyse du portefeuille crypto : {wallet}...")

        is_btc = re.match(r"^(1|3|bc1)[a-zA-HJ-NP-Z0-9]{25,39}$", wallet)
        is_eth = re.match(r"^0x[a-fA-F0-9]{40}$", wallet)

        coin_type = "BTC" if is_btc else "ETH" if is_eth else "Unknown"
        
        if coin_type == "Unknown":
            return {"status": "error", "message": "Format d'adresse crypto non reconnu."}

        # Ajout direct dans le graphe d'investigation
        node_id = f"crypto_{wallet}"
        await self.core.context.add_entity(node_id, f"CryptoWallet_{coin_type}", wallet)

        return {
            "address": wallet,
            "blockchain": coin_type,
            "status": "validated"
        }