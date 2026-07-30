import asyncio
from typing import Any, Dict
from langdetect import detect
from deep_translator import GoogleTranslator


class DataLanguageNormalizer:
    """Ingère les données multi-langues et les traduit automatiquement vers la langue cible."""
    def __init__(self, target_language: str = "en") -> None:
        self.target_lang = target_language

    async def normalize_payload(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = raw_data.copy()
        loop = asyncio.get_running_loop()

        for key, value in raw_data.items():
            if isinstance(value, str) and len(value) > 15:
                try:
                    src_lang = detect(value)
                    if src_lang != self.target_lang:
                        translator = GoogleTranslator(source=src_lang, target=self.target_lang)
                        translated = await loop.run_in_executor(None, translator.translate, value)
                        normalized[f"{key}_translated"] = translated
                        normalized[f"{key}_original_lang"] = src_lang
                except Exception:
                    pass
        return normalized