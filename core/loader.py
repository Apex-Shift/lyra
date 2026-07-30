import importlib.util
import os
from pathlib import Path
from typing import Any, Dict

class ModuleLoader:
    def __init__(self, core_instance: Any) -> None:
        self.core = core_instance
        self.modules: Dict[str, Any] = {}
        self.modules_dir = Path(__file__).parent.parent / "modules"

    def load_all_modules(self) -> None:
        if not self.modules_dir.exists():
            return
        for file_path in self.modules_dir.rglob("*.py"):
            if file_path.name == "__init__.py":
                continue
            relative_path = file_path.relative_to(self.modules_dir)
            module_key = str(relative_path.with_suffix("")).replace(os.sep, "/")
            try:
                spec = importlib.util.spec_from_file_location(module_key, file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "Module"):
                        instance = mod.Module()
                        instance.core = self.core
                        self.modules[module_key] = instance
            except Exception as e:
                print(f"[-] Failure loading module {module_key}: {e}")

    def get_module(self, module_path: str) -> Any:
        if module_path in self.modules:
            return self.modules[module_path]
        raise KeyError(f"Module {module_path} not found.")
