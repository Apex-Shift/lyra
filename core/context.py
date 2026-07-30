import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

class TargetEntity:
    def __init__(self, entity_id: str, entity_type: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.id: str = entity_id
        self.type: str = entity_type
        self.value: str = value
        self.metadata: Dict[str, Any] = metadata or {}
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type, "value": self.value, "metadata": self.metadata, "created_at": self.created_at}

class TargetPivot:
    def __init__(self, source_id: str, target_id: str, relation: str, module_source: str) -> None:
        self.source: str = source_id
        self.target: str = target_id
        self.relation: str = relation
        self.module_source: str = module_source
        self.timestamp: str = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target, "relation": self.relation, "module_source": self.module_source, "timestamp": self.timestamp}

class InvestigationContext:
    def __init__(self, case_id: str = "DEFAULT_CASE") -> None:
        self.case_id: str = case_id
        self.entities: Dict[str, TargetEntity] = {}
        self.pivots: List[TargetPivot] = []
        self._lock = asyncio.Lock()

    async def add_entity(self, entity_id: str, entity_type: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> TargetEntity:
        async with self._lock:
            if entity_id not in self.entities:
                entity = TargetEntity(entity_id, entity_type, value, metadata)
                self.entities[entity_id] = entity
            else:
                if metadata:
                    self.entities[entity_id].metadata.update(metadata)
            return self.entities[entity_id]

    async def add_pivot(self, source_id: str, target_id: str, relation: str, module_source: str) -> None:
        async with self._lock:
            self.pivots.append(TargetPivot(source_id, target_id, relation, module_source))

    def get_graph_data(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "nodes": [e.to_dict() for e in self.entities.values()],
            "edges": [p.to_dict() for p in self.pivots()]
        }
