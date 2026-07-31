# Lyra — OSINT Framework

Lyra is a lightweight OSINT framework for orchestrating modules, exporting investigation graphs as forensic JSON, and storing investigation artifacts in a local SQLite store. The project provides both a programmatic API and a desktop control GUI.

This README documents the repository structure, how to run the API and GUI, how to use the library from Python, the export format, storage schema, testing, CLI usage, and recommended development practices.

---

## Table of contents

- Project overview
- Key features
- Repository layout
- Quick start
  - Prerequisites
  - Install
  - Run API
  - Run GUI
- Programmatic usage examples
  - InvestigationContext
  - LyraExporter
  - StorageManager
- Forensic JSON export format
- Storage (SQLite) schema
- CLI usage
- Tests
- Developer workflow
- Recommended follow-ups
- Contributing
- License & contact

---

## Project overview

Lyra provides:
- A central InvestigationContext to collect Entities (nodes) and Pivots (edges).
- An exporter to write a deterministic, signed forensic JSON file.
- A StorageManager that ingests graph payloads into a local SQLite database.
- A PySide6 GUI (Control Center) to list and run modules via a simple HTTP API.

The project focuses on reliability and compatibility:
- Exporter produces canonical JSON and a SHA-256 payload signature.
- Storage accepts current and legacy payload shapes and tolerates minor differences in field names.

---

## Key features

- Programmatic API to build an investigation graph.
- Deterministic forensic JSON export with chain-of-custody signature.
- Robust ingestion into SQLite (idempotent where appropriate).
- Desktop GUI for interactive module execution (via API).
- Small pytest scaffold to validate an end-to-end roundtrip.

---

## Repository layout

Typical important files and folders:

- core/
  - context.py          — InvestigationContext, TargetEntity, TargetPivot
  - exporter.py         — LyraExporter (forensic JSON writer)
- lyra_gui.py           — PySide6 Control Center GUI
- storage.py            — StorageManager (aiosqlite)
- tests/                — pytest tests (e.g., tests/test_roundtrip.py)
- requirements.txt      — Python dependencies

---

## Quick start

### Prerequisites

- Python 3.10+ recommended
- pip
- For GUI: PySide6
- For async SQLite: aiosqlite
- For HTTP client (GUI): httpx

### Installation

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the API

Start the local HTTP API backend server to expose modules:

```bash
python lyra_cli.py --api
```

The GUI connects to this local endpoint at `http://127.0.0.1:8000` by default.

### Run the GUI

Launch the PySide6 control center application:

```bash
python lyra_gui.py
```


- The GUI will attempt to contact the API (`/modules`) and show modules.
- Enter module option values in the form. The GUI preserves typed values where possible:
  - It first attempts `json.loads()` on the input, so `true`, `false`, `null`, numbers, arrays and objects are preserved.
  - If JSON parsing fails, safe fallbacks are applied (booleans and integers).

---

## Programmatic usage

Below are example snippets you can use inside Python scripts or tests.

### InvestigationContext (build a graph)

```python
from core.context import InvestigationContext
import asyncio

ctx = InvestigationContext(case_id="CASE-001")

# Add entities (async)
async def build_context():
    await ctx.add_entity("e1", "ip", "1.2.3.4", {"source": "scan"})
    await ctx.add_entity("e2", "domain", "example.com", {"source": "dns"})
    await ctx.add_pivot("e1", "e2", "resolves_to", "dns-module")

asyncio.run(build_context())

graph = ctx.get_graph_data()
# graph -> {"nodes": [...], "edges": [...]} 
```


### LyraExporter (export forensic JSON with signature)

```python
from core.exporter import LyraExporter
import asyncio

exporter = LyraExporter(export_dir="exports")

# nodes and edges come from ctx.get_graph_data()
nodes = graph["nodes"]
edges = graph["edges"]

out_path = asyncio.run(exporter.to_forensic_json("CASE-001", nodes, edges, operator_name="Analyst1"))
print("Export written to:", out_path)
```

Notes:
- The exporter writes `graph_data` as `{ "nodes": [...], "edges": [...] }` and includes deterministic metadata plus a `payload_hash_signature` (SHA-256).
- The signature is computed over canonical JSON (sorted keys and compact separators) to avoid accidental ordering differences.

### StorageManager (save to SQLite)

```python
from storage import StorageManager
import asyncio

sm = StorageManager(db_path="exports/lyra_investigations.db")
# Accepts either {"nodes","edges"} or legacy {"entities","relations"} shapes
asyncio.run(sm.save_case_graph("CASE-001", {"nodes": nodes, "edges": edges}))
```

Storage behaviors:
- Creates `cases`, `entities`, and `pivots` tables if missing.
- `entities` rows are inserted with `INSERT OR REPLACE` (idempotent).
- `pivots` rows are inserted; the ingestion code tolerates alternate keys (e.g., `src`, `dst`, `target_id`) and skips malformed entries.

---

## Forensic JSON export format

The exporter produces a forensic JSON file with this structure:

```json
{
  "metadata": {
    "framework": "Lyra OSINT Framework v1.0.0",
    "case_id": "CASE-001",
    "generated_at_utc": "2026-07-31T...Z",
    "investigator": "Analyst",
    "integrity_protocol": "SHA-256 Chain-of-Custody",
    "payload_hash_signature": "..."
  },
  "graph_data": {
    "nodes": [
      { "id": "e1", "type": "ip", "value": "1.2.3.4", "metadata": {...}, "created_at": "..." }
    ],
    "edges": [
      { "source": "e1", "target": "e2", "relation": "resolves_to", "module_source": "dns-module", "timestamp": "..." }
    ]
  }
}
```

Important:
- `payload_hash_signature` is computed over canonical JSON of the payload before inserting the `payload_hash_signature` field; this provides a repeatable integrity check for chain-of-custody.

---

## Storage (SQLite) schema

StorageManager creates these tables:

- cases
  - case_id TEXT PRIMARY KEY
  - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  - notes TEXT

- entities
  - id TEXT PRIMARY KEY
  - case_id TEXT
  - type TEXT
  - value TEXT
  - metadata TEXT (JSON encoded)
  - created_at TIMESTAMP

- pivots
  - id INTEGER PRIMARY KEY AUTOINCREMENT
  - case_id TEXT
  - source_id TEXT
  - target_id TEXT
  - relation TEXT
  - module_source TEXT
  - timestamp TIMESTAMP

Notes:
- `metadata` for entities is stored as a JSON string.
- Storage ingestion attempts to be tolerant — missing or alternate field names are handled where possible.

---

## CLI Usage

Lyra provides a command-line interface to orchestrate modules, run the local API server, and interact with the storage components.

### Prerequisites

- Python 3.10+
- Active virtual environment (`.venv`)
- Core dependencies installed via `pip install -r requirements.txt`

### Passing JSON Options via CLI

When passing typed arguments or JSON payloads via the terminal, ensure proper shell quoting based on your operating system:

*   **Linux / macOS (bash/zsh):** Use single quotes around the JSON string.
    ```bash
    '{"target": "example.com", "limit": 10}'
    ```
*   **Windows (cmd.exe):** Use double quotes and escape internal quotes with backslashes.
    ```cmd
    "{\"target\":\"example.com\",\"limit\":10}"
    ```

### Common Commands

#### 1. Start the API Server
Launch the backend server to handle module execution (defaults to port `8000`):
```bash
python lyra_cli.py --api --host 127.0.0.1 --port 8000
```

#### 2. Run the Desktop GUI
Start the PySide6 control center application. It automatically connects to the running local API:
```bash
python lyra_gui.py
```

#### 3. Execute a Module via API (curl)
```bash
curl -X POST "http://127.0.0" \
  -H "Content-Type: application/json" \
  -d '{"options":{"target":"example.com","limit":10,"include_subdomains":true}}'
```

Example using httpie:
```bash
http POST http://127.0.0.1:8000/modules/some/module/path/run options:='{"target": "example.com", "limit": 10}'
```

4) Quick-run a module locally via Python (one-liner / script)
```bash
python - <<'PY'
from core.context import InvestigationContext
from core.exporter import LyraExporter
from storage import StorageManager
import asyncio, json

# build context
ctx = InvestigationContext("CLI_CASE")
asyncio.run(ctx.add_entity("e1","ip","1.2.3.4"))
asyncio.run(ctx.add_entity("e2","domain","example.com"))
asyncio.run(ctx.add_pivot("e1","e2","resolves_to","cli"))

graph = ctx.get_graph_data()
# export
exporter = LyraExporter(export_dir="exports")
out = asyncio.run(exporter.to_forensic_json("CLI_CASE", graph["nodes"], graph["edges"], "cli-user"))
print("Exported:", out)
PY
```

5) Export a case to forensic JSON from a saved graph (example)
- If you have built a graph in Python you can call LyraExporter as above.
- The exporter writes a canonical JSON and appends metadata.payload_hash_signature (SHA-256).

6) Initialize or inspect the Storage DB and ingest a graph via CLI
```bash
python - <<'PY'
import json
from storage import StorageManager
import asyncio

sm = StorageManager(db_path="exports/lyra_investigations.db")
# load an exported forensic json
payload = json.load(open("exports/CASE_CLI_CASE_1630000000.json", encoding="utf-8"))
graph_data = payload.get("graph_data", {})  # accepts {"nodes","edges"} or {"entities","relations"}
asyncio.run(sm.save_case_graph("CLI_CASE", graph_data))
print("Saved to DB")
PY
```
Quick DB inspection (sqlite3 CLI):
```bash
sqlite3 exports/lyra_investigations.db "SELECT case_id, COUNT(*) FROM entities GROUP BY case_id;"
```

7) Run the test scaffold
```bash
pip install pytest
pytest -q tests/test_roundtrip.py
```

### Suggested CLI improvements (future)
- Add a small CLI wrapper script (e.g., `cli.py`) using argparse or typer to expose common operations:
  - `cli.py api --host 127.0.0.1 --port 8000`
  - `cli.py gui`
  - `cli.py run-module --module some/module/path --options '{"target":"..." }'`
  - `cli.py export-case --case CASE_ID --out exports/CASE.json`
  - `cli.py ingest --file exports/CASE.json`
- Using a wrapper provides consistent UX, built-in help, and consistent option parsing (and allows automatic shell completion when using typer/click).

---

## Tests

A pytest end-to-end test scaffold is included in `tests/test_roundtrip.py`. It validates the roundtrip:

InvestigationContext → LyraExporter → StorageManager

Run tests:

```bash
pytest -q tests/test_roundtrip.py
```

If tests fail:
- Check the virtual environment and installed dependencies.
- Ensure the repo branch with the changes is checked out.

---

## Developer workflow & recommendations

- Branching: create short-lived feature branches (example: `fix/context-exporter-storage-compat`).
- Formatting: use `black` and `isort`.
- Static typing: consider `mypy` (type hints help stability).
- Logging: replace ad-hoc `print()` calls with `logging` and configurable log levels.
- CI: add GitHub Actions to run `pytest` and linters on PRs.

Recommended GitHub Actions (follow-up):
- `python-app.yml` that runs tests (pytest), black/isort check, and optionally mypy.

---

## Contributing

- Fork the repository and open a PR.
- Run tests locally before opening PRs.
- Keep commits small and focused; include a clear PR description and rationale.

Please be mindful if the project touches privacy-sensitive information: follow applicable laws and internal policies when collecting/storing any data.

---

## Roadmap (Future Improvements)

Here are the next steps planned for the development of Lyra:
- Create a `Makefile` to simplify common commands (`venv`, `install`, `test`).
- Set up a GitHub Actions workflow to automatically run tests on every Pull Request.
- Add comprehensive developer documentation (`CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`).
- Add strict validation tests for edge cases, malformed nodes, and empty inputs.

---

## Contributing

Contributions are welcome! If you would like to help build Lyra, please fork the repository and open a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

## License & Contact

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

For support, bug reports, or questions, please open an issue directly on the [GitHub issue tracker](https://github.com).
