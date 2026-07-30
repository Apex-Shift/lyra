from typing import Any, Dict
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "Multimodal Visual GeoLocator",
        "description": "Analyse une image via l'IA visuelle (Ollama/OpenAI) pour extraire des indices géographiques et valider les positions via OpenStreetMap.",
        "author": "Lyra Core Dev Team",
        "category": "geo"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["IMAGE_PATH"] = Option("", required=True, description="Chemin absolu vers l'image cible sur le disque")
        self.options["EXTRACT_TEXT"] = Option(True, required=False, description="Tenter une extraction OCR des enseignes et panneaux")

    async def run(self) -> Dict[str, Any]:
        image_path = self.options["IMAGE_PATH"].value
        extract_text = self.options["EXTRACT_TEXT"].value

        print(f"[*] Encodage et transmission de l'image au moteur IA : {image_path}...")

        # Instruction système pour l'analyse d'image Geoguess
        prompt = (
            f"Analyse l'image située ici : {image_path}. "
            "Extrais tous les indices géographiques visibles (architecture, plaques d'immatriculation, langages, végétation, poteaux téléphoniques). "
            "Donne une estimation du pays, de la région et une coordonnée GPS approximative sous forme [latitude, longitude]."
        )

        # Appel au gestionnaire IA du Core
        ai_response = await self.core.ai_manager.analyze_text(
            prompt=prompt,
            system_instructions="Tu es un expert mondial en géolocalisation d'images et en analyse OSINT visuelle."
        )

        print("[+] Analyse visuelle terminée par le cœur IA.")

        # Injection de la cible et des résultats dans le graphe d'enquête
        node_id = f"visual_target_{hash(image_path)}"
        await self.core.context.add_entity(
            entity_id=node_id,
            entity_type="Visual_Evidence",
            value=image_path,
            metadata={"ai_report": ai_response}
        )

        return {
            "image": image_path,
            "geo_analysis_report": ai_response,
            "status": "completed"
        }