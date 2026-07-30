import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

class LyraExporter:
    def __init__(self, export_dir: str = "exports") -> None:
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def _generate_sha256(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    async def to_forensic_json(self, case_id: str, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], operator_name: str) -> Path:
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "metadata": {
                "framework": "Lyra OSINT Framework v1.0.0",
                "case_id": case_id,
                "generated_at_utc": timestamp,
                "investigator": operator_name,
                "integrity_protocol": "SHA-256 Chain-of-Custody"
            },
            "graph_data": {"entities": nodes, "relations": edges}
        }
        raw_json = json.dumps(payload, indent=2, ensure_ascii=False)
        payload["metadata"]["payload_hash_signature"] = self._generate_sha256(raw_json)
        file_path = self.export_dir / f"CASE_{case_id}_{int(datetime.now().timestamp())}.json"
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"))
        print(f"[+] [Exporter] Forensic JSON exported to: {file_path}")
        return file_path
