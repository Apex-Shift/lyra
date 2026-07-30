from abc import ABC, abstractmethod
from typing import Any, Dict

class Option:
    def __init__(self, default: Any, required: bool = True, description: str = "") -> None:
        self.value: Any = default
        self.required: bool = required
        self.description: str = description

class BaseModule(ABC):
    meta: Dict[str, str] = {
        "name": "Base Module",
        "description": "Base template specification",
        "author": "Lyra Dev Team",
        "category": "base"
    }

    def __init__(self) -> None:
        self.options: Dict[str, Option] = {}
        self.core: Any = None

    def set_option(self, key: str, value: Any) -> None:
        if key in self.options:
            self.options[key].value = value
        else:
            raise KeyError(f"[-] Unknown option: {key}")

    @abstractmethod
    async def run(self) -> Dict[str, Any]:
        pass
