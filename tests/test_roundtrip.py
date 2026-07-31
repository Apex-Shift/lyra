import asyncio
import json
from pathlib import Path
from core.context import InvestigationContext
from core.exporter import LyraExporter
from storage import StorageManager


def test_roundtrip(tmp_path: Path) -> None:
    """End-to-end roundtrip test: InvestigationContext -> LyraExporter -> StorageManager

    This test creates a small context with two entities and a pivot, exports it to forensic JSON,
    then saves it into the StorageManager SQLite DB and verifies that records exist.
    """
    # Setup
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    ctx = InvestigationContext(case_id="TESTCASE")
    # add entities and pivot using asyncio run to call async methods
    asyncio.run(ctx.add_entity("e1", "ip", "1.2.3.4", {"source": "unittest"}))
    asyncio.run(ctx.add_entity("e2", "domain", "example.com", {"source": "unittest"}))
    asyncio.run(ctx.add_pivot("e1", "e2", "resolves_to", "unit-test-module"))

    # Export
    graph = ctx.get_graph_data()
    exporter = LyraExporter(export_dir=str(exports_dir))
    out_path = asyncio.run(exporter.to_forensic_json("TESTCASE", graph["nodes"], graph["edges"], "tester"))
    assert Path(out_path).exists()

    # Load payload and save to storage
    payload = json.loads(Path(out_path).read_text(encoding="utf-8"))
    storage_db = tmp_path / "investigations.db"
    sm = StorageManager(db_path=str(storage_db))

    # Save using the graph_data from the export to mimic an ingestion pipeline
    asyncio.run(sm.save_case_graph("TESTCASE", payload.get("graph_data", {})))

    # Quick DB checks
    import sqlite3

    conn = sqlite3.connect(str(storage_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM entities WHERE case_id = ?", ("TESTCASE",))
    entities_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(1) FROM pivots WHERE case_id = ?", ("TESTCASE",))
    pivots_count = cur.fetchone()[0]
    conn.close()

    assert entities_count >= 2
    assert pivots_count >= 1
