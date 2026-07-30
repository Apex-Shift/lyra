import asyncio
import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn


class ModuleOptionPayload(BaseModel):
    options: Dict[str, Any]


class TaskManager:
    """Gère le suivi des exécutions asynchrones en arrière-plan."""
    def __init__(self) -> None:
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {"status": "pending", "result": None}
        return task_id

    def update_task(self, task_id: str, status: str, result: Any = None) -> None:
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            if result is not None:
                self.tasks[task_id]["result"] = result


class APIServerManager:
    """Expose le moteur Lyra via une API REST FastAPI ultra-rapide."""
    def __init__(self, core_instance: Any) -> None:
        self.core = core_instance
        self.task_manager = TaskManager()
        self.app = FastAPI(
            title="🌌 Lyra OSINT API",
            description="Interface de contrôle asynchrone et programmable pour Lyra OSINT Framework.",
            version="1.0.0"
        )
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.get("/modules", tags=["Registry"])
        async def list_modules():
            """Retourne la liste globale de tous les modules dynamic-loaded."""
            return {
                "total_modules": len(self.core.loader.modules),
                "modules": [
                    {
                        "name": key,
                        "metadata": mod.meta,
                        "options": {
                            name: {
                                "value": o.value,
                                "required": o.required,
                                "description": o.description
                            } for name, o in mod.options.items()
                        }
                    }
                    for key, mod in self.core.loader.modules.items()
                ]
            }

        @self.app.post("/modules/{module_path:path}/run", tags=["Orchestration"])
        async def run_module_sync(module_path: str, payload: ModuleOptionPayload):
            """Exécute un module en mode bloquant direct HTTP."""
            try:
                module = self.core.loader.get_module(module_path)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"Module '{module_path}' introuvable.")

            try:
                for opt_name, opt_value in payload.options.items():
                    module.set_option(opt_name, opt_value)
            except KeyError as e:
                raise HTTPException(status_code=400, detail=str(e))

            result = await module.run()
            return {"module": module_path, "status": "success", "payload": result}

        @self.app.post("/modules/{module_path:path}/run-async", tags=["Orchestration"])
        async def run_module_async(module_path: str, payload: ModuleOptionPayload, bg_tasks: BackgroundTasks):
            """Lance un module lourd en tâche de fond (retourt immédiat d'un task_id)."""
            try:
                module = self.core.loader.get_module(module_path)
                for opt_name, opt_value in payload.options.items():
                    module.set_option(opt_name, opt_value)
            except KeyError as e:
                raise HTTPException(status_code=400, detail=str(e))

            task_id = self.task_manager.create_task()
            bg_tasks.add_task(self._async_worker, task_id, module)
            return {"task_id": task_id, "status": "queued"}

        @self.app.get("/tasks/{task_id}", tags=["Tasks"])
        async def get_task_status(task_id: str):
            """Consulte l'état et le résultat d'une tâche asynchrone."""
            if task_id not in self.task_manager.tasks:
                raise HTTPException(status_code=404, detail="Task ID non trouvé.")
            return self.task_manager.tasks[task_id]

    async def _async_worker(self, task_id: str, module_instance: Any) -> None:
        self.task_manager.update_task(task_id, "running")
        try:
            res = await module_instance.run()
            self.task_manager.update_task(task_id, "completed", res)
        except Exception as e:
            self.task_manager.update_task(task_id, "failed", {"error": str(e)})

    def start(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        print(f"[+] [API Core] Activation du serveur HTTP sur http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port, log_level="warning")