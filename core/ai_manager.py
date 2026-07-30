from typing import Any, Dict, Optional
import httpx


class AIManager:
    """Interface unifiée IA : gère les LLMs locaux (Ollama) et distants (OpenAI)."""
    def __init__(self, config: Dict[str, Any]) -> None:
        cfg = config.get("ai_settings", {})
        self.provider: str = cfg.get("provider", "ollama").lower()
        self.model_name: str = cfg.get("model_name", "llama3")
        self.api_url: str = cfg.get("api_url", "http://localhost:11434")
        self.api_key: Optional[str] = cfg.get("api_key")

    async def analyze_text(self, prompt: str, system_instructions: str = "") -> str:
        if self.provider == "ollama":
            return await self._query_ollama(prompt, system_instructions)
        elif self.provider == "openai":
            return await self._query_openai(prompt, system_instructions)
        return "[-] Erreur : Provider IA non pris en charge."

    async def _query_ollama(self, prompt: str, system: str) -> str:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.api_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": f"{system}\n\n{prompt}",
                        "stream": False
                    },
                    timeout=60.0
                )
                if res.status_code == 200:
                    return res.json().get("response", "")
                return f"[-] Erreur Ollama ({res.status_code}): {res.text}"
            except Exception as e:
                return f"[-] IA locale hors ligne : {e}"

    async def _query_openai(self, prompt: str, system: str) -> str:
        if not self.api_key:
            return "[-] Clé d'API OpenAI manquante."

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model_name or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                return f"[-] Erreur OpenAI ({res.status_code}): {res.text}"
            except Exception as e:
                return f"[-] Échec de la requête OpenAI : {e}"