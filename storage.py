import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite


class StorageManager:
    """Moteur de persistance SQLite asynchrone pour l'archivage forensique."""
    def __init__(self, db_path: str = "exports/lyra_investigations.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    case_id TEXT,
                    type TEXT,
                    value TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pivots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id TEXT,
                    source_id TEXT,
                    target_id TEXT,
                    relation TEXT,
                    module_source TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                )
            """)
            await db.commit()

    async def save_case_graph(self, case_id: str, graph_data: Dict[str, List[Dict[str, Any]]]) -> None:
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO cases (case_id) VALUES (?)", (case_id,))
            
            # Insertion des nœuds (Entities)
            for node in graph_data.get("nodes", []):
                await db.execute(
                    """
                    INSERT OR REPLACE INTO entities (id, case_id, type, value, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node["id"],
                        case_id,
                        node["type"],
                        node["value"],
                        json.dumps(node.get("metadata", {})),
                        node.get("created_at")
                    )
                )

            # Insertion des relations (Edges / Pivots)
            for edge in graph_data.get("edges", []):
                await db.execute(
                    """
                    INSERT INTO pivots (case_id, source_id, target_id, relation, module_source, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        edge["source"],
                        edge["target"],
                        edge["relation"],
                        edge["module_source"],
                        edge["timestamp"]
                    )
                )
            await db.commit()