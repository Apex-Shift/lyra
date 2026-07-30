from typing import Any, Dict
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from core.base_module import BaseModule, Option


class Module(BaseModule):
    meta = {
        "name": "EXIF Forensics & GPS Extractor",
        "description": "Analyse un fichier image local pour extraire ses métadonnées cachées (EXIF), le modèle d'appareil et la position GPS exacte.",
        "author": "Lyra Core Dev Team",
        "category": "geo"
    }

    def __init__(self) -> None:
        super().__init__()
        self.options["IMAGE_PATH"] = Option("", required=True, description="Chemin absolu vers l'image (.jpg/.jpeg/.png)")

    async def run(self) -> Dict[str, Any]:
        image_path = self.options["IMAGE_PATH"].value
        print(f"[*] Extraction des données forensiques EXIF pour : {image_path}...")

        exif_data = {}
        try:
            img = Image.open(image_path)
            info = img._getexif()

            if not info:
                return {"status": "warning", "message": "Aucune donnée EXIF présente dans cette image."}

            for tag_id, value in info.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_tag = GPSTAGS.get(t, t)
                        gps_data[sub_tag] = value[t]
                    exif_data["GPSInfo"] = gps_data
                else:
                    exif_data[str(tag)] = str(value)

            # Ingestion dans le graphe
            node_id = f"exif_{hash(image_path)}"
            await self.core.context.add_entity(node_id, "Media_Forensics", image_path, {"exif_keys_count": len(exif_data)})

            print(f"[+] {len(exif_data)} métadonnée(s) extraite(s) avec succès.")
            return {"status": "success", "file": image_path, "exif": exif_data}

        except Exception as e:
            return {"status": "error", "message": f"Échec de lecture du fichier image : {e}"}