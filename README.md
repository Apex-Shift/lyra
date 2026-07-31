# Lyra — OSINT Framework

Lyra is a lightweight OSINT framework for orchestrating modules, exporting investigation graphs as forensic JSON, and storing investigation artifacts in a local SQLite database. The repository contains a programmatic API, a desktop GUI, and tools for exporting and ingesting investigation data.

## Table of contents

- Project overview
- Features
- Repository layout
- Quick start
  - Prerequisites
  - Install
  - Run API
  - Run GUI
- Programmatic usage
  - InvestigationContext
  - LyraExporter
  - StorageManager
- Forensic JSON format
- Storage schema
- CLI usage
- Tests
- Developer workflow
- Contributing
- License & contact

## Project overview

Lyra provides:
- InvestigationContext for collecting Entities (nodes) and Pivots (edges).
- LyraExporter for writing deterministic forensic JSON with a SHA-256 payload signature.
- StorageManager for ingesting graph payloads into a local SQLite database.
- A PySide6 GUI (lyra_gui.py) that interacts with a local API to list and run modules.

## Features

- Build an investigation graph programmatically.
- Export a signed forensic JSON file.
- Ingest graphs into SQLite for persistence and querying.
- Desktop GUI for module execution via the API.
- Basic pytest test verifying an end-to-end roundtrip.

## Repository layout

- core/
  - context.py       — InvestigationContext, TargetEntity, TargetPivot
  - exporter.py      — LyraExporter (forensic JSON writer)
- lyra_gui.py        — PySide6 Control Center GUI
- storage.py         — StorageManager (aiosqlite)
- tests/             — pytest tests (tests/test_roundtrip.py)
- README.md          — this document
- requirements.txt   — Python dependencies

## Quick start

### Prerequisites

- Python 3.10+
- pip
- For GUI: PySide6
- For async SQLite: aiosqlite
- For HTTP client (GUI): httpx

### Install

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If needed:

```bash
pip install PySide6 httpx aiosqlite pytest
```

### Run the API

If the repository includes an API entrypoint (e.g., `lyra.py`), start it:

```bash
python lyra.py --api
```

The GUI uses `http://127.0.0.1:8000` by default. Adjust API host/port as necessary.

### Run the GUI

```bash
python lyra_gui.py
```

The GUI fetches available modules from the API and provides a form to run them. Input values entered in the GUI are parsed to preserve JSON types when possible.

## Programmatic usage

### InvestigationContext

```python
from core.context import InvestigationContext
import asyncio

ctx = InvestigationContext(case_id="CASE-001")

async def build():
    await ctx.add_entity("e1", "ip", "1.2.3.4", {"source": "scan"})
    await ctx.add_entity("e2", "domain", "example.com", {"source": "dns"})
    await ctx.add_pivot("e1", "e2", "resolves_to", "dns-module")

asyncio.run(build())

graph = ctx.get_graph_data()
# graph -> {"nodes": [...], "edges": [...]}
```

### LyraExporter

```python
from core.exporter import LyraExporter
import asyncio

exporter = LyraExporter(export_dir="exports")
out_path = asyncio.run(exporter.to_forensic_json("CASE-001", graph["nodes"], graph["edges"], operator_name="Analyst1"))
print(out_path)
```

### StorageManager

```python
from storage import StorageManager
import asyncio

sm = StorageManager(db_path="exports/lyra_investigations.db")
asyncio.run(sm.save_case_graph("CASE-001", graph))
```

StorageManager accepts graph payloads using either `{"nodes","edges"}` or legacy `{"entities","relations"}` naming and stores entities and pivots in SQLite tables.

## Forensic JSON format

Exported forensic JSON contains metadata and graph_data. Example structure:

```json
{
  "metadata": {
    "framework": "Lyra OSINT Framework v1.0.0",
    "case_id": "CASE-001",
    "generated_at_utc": "...",
    "investigator": "Analyst",
    "integrity_protocol": "SHA-256 Chain-of-Custody",
    "payload_hash_signature": "..."
  },
  "graph_data": {
    "nodes": [ ... ],
    "edges": [ ... ]
  }
}
```

The `payload_hash_signature` is a SHA-256 value computed over a canonical JSON representation of the payload before the signature field is added.

## Storage schema

Tables created by StorageManager:

- cases(case_id TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, notes TEXT)
- entities(id TEXT PRIMARY KEY, case_id TEXT, type TEXT, value TEXT, metadata TEXT, created_at TIMESTAMP)
- pivots(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, source_id TEXT, target_id TEXT, relation TEXT, module_source TEXT, timestamp TIMESTAMP)

## CLI usage

Common tasks and examples.

Run the API (example):

```bash
python lyra.py --api --host 127.0.0.1 --port 8000
```

Run the GUI:

```bash
python lyra_gui.py
```

Run a module via the API (curl):

```bash
curl -X POST "http://127.0.0.1:8000/modules/some/module/path/run" \
  -H "Content-Type: application/json" \
  -d '{"options":{"target":"example.com","limit":10,"include_subdomains":true}}'
```

Quick-run a module locally (Python):

```bash
python - <<'PY'
from core.context import InvestigationContext
from core.exporter import LyraExporter
from storage import StorageManager
import asyncio

ctx = InvestigationContext("CLI_CASE")
asyncio.run(ctx.add_entity("e1","ip","1.2.3.4"))
asyncio.run(ctx.add_entity("e2","domain","example.com"))
asyncio.run(ctx.add_pivot("e1","e2","resolves_to","cli"))

graph = ctx.get_graph_data()
exporter = LyraExporter(export_dir="exports")
print(asyncio.run(exporter.to_forensic_json("CLI_CASE", graph["nodes"], graph["edges"], "cli-user")))
PY
```

Ingest an exported graph into the storage DB:

```bash
python - <<'PY'
import json
from storage import StorageManager
import asyncio

payload = json.load(open("exports/CASE.json", encoding="utf-8"))
graph_data = payload.get("graph_data", {})
sm = StorageManager(db_path="exports/lyra_investigations.db")
asyncio.run(sm.save_case_graph("CASE", graph_data))
PY
```

Notes on CLI JSON quoting:
- On Unix shells use single quotes to wrap JSON payloads: '{"key": true }'
- On Windows use double quotes and escape inner quotes.

## Tests

Run the pytest test included in `tests/test_roundtrip.py`:

```bash
pytest -q tests/test_roundtrip.py
```

## Developer workflow

- Use feature branches for changes.
- Keep commits focused and descriptive.
- Run tests locally before pushing changes.

## Contributing

Fork the repository and open a pull request with a clear description of the change.

Follow applicable laws and organizational policies when collecting or storing data.

## License & contact

Add a LICENSE file to specify terms. For issues or questions, open an issue in this repository.
