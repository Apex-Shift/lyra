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
        # Accept both {"nodes": [...], "edges": [...]} and {"entities": [...], "relations": [...]}
        await self.init_db()
        nodes = graph_data.get("nodes") or graph_data.get("entities") or []
        edges = graph_data.get("edges") or graph_data.get("relations") or []

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO cases (case_id) VALUES (?)", (case_id,))

            # Insertion des nœuds (Entities)
            for node in nodes:
                node_id = node.get("id")
                if not node_id:
                    # skip invalid node
                    continue
                await db.execute(
                    """
                    INSERT OR REPLACE INTO entities (id, case_id, type, value, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node_id,
                        case_id,
                        node.get("type"),
                        node.get("value"),
                        json.dumps(node.get("metadata", {})),
                        node.get("created_at")
                    )
                )

            # Insertion des relations (Edges / Pivots)
            for edge in edges:
                # tolerate both "source" or "src" naming if present
                source = edge.get("source") or edge.get("src")
                target = edge.get("target") or edge.get("dst") or edge.get("target_id")
                relation = edge.get("relation") or edge.get("rel")
                module_source = edge.get("module_source") or edge.get("module")
                timestamp = edge.get("timestamp")
                if not (source and target):
                    # skip incomplete edge
                    continue
                await db.execute(
                    """
                    INSERT INTO pivots (case_id, source_id, target_id, relation, module_source, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        source,
                        target,
                        relation,
                        module_source,
                        timestamp
                    )
                )
            await db.commit()
