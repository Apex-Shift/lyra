import asyncio
import sys
from typing import Any, List
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

try:
    import mmh3
except ImportError:
    mmh3 = None

class LyraCompleter(Completer):
    """Autocompléteur dynamique pour les commandes et répertoires de modules."""
    def __init__(self, cli_instance: Any) -> None:
        self.cli = cli_instance
        self.base_commands = ["show modules", "show options", "use", "set", "back", "run", "export", "help", "exit"]

    def get_completions(self, document: Document, complete_event: Any):
        text = document.text_before_cursor
        words = text.split()

        if not words:
            for cmd in self.base_commands:
                yield Completion(cmd, start_position=0)
        elif len(words) == 1:
            for cmd in self.base_commands:
                if cmd.startswith(words[0]):
                    yield Completion(cmd, start_position=-len(words[0]))

class LyraCLI:
    def __init__(self, core_instance: Any) -> None:
        self.core = core_instance
        self.session = PromptSession(completer=LyraCompleter(self))
        self.current_module = None

    async def _handle_command(self, cmd_line: str) -> bool:
        cmd_line = cmd_line.strip()
        if not cmd_line:
            return True

        if cmd_line in ["exit", "quit"]:
            return False

        if cmd_line == "help":
            print("\n[+] Commandes disponibles :")
            print("  show modules  - Liste les modules OSINT disponibles")
            print("  use <module>  - Sélectionne un module")
            print("  show options  - Affiche les options du module sélectionné")
            print("  set <k> <v>   - Définit une option")
            print("  run           - Exécute le module courant")
            print("  exit          - Quitte le programme\n")
            return True

        if cmd_line == "show modules":
            print("\n[+] Modules chargés dans le core :")
            if hasattr(self.core, "loader") and self.core.loader.modules:
                for mod_name in self.core.loader.modules.keys():
                    print(f"  - {mod_name}")
            else:
                print("  [-] Aucun module trouvé dans /modules.")
            print()
            return True

        print(f"[-] Commande inconnue: {cmd_line}. Tape 'help' pour la liste.")
        return True

    async def start(self) -> None:
        """Méthode d'entrée principale de la CLI."""
        print("🌌 Terminal interactif Lyra OSINT")
        if mmh3 is None:
            print("[!] Attention: la bibliothèque 'mmh3' n'est pas installée.")
        
        while True:
            try:
                user_input = await self.session.prompt_async("lyra > ")
                should_continue = await self._handle_command(user_input)
                if not should_continue:
                    print("[+] Fermeture de Lyra OSINT.")
                    break
            except (KeyboardInterrupt, EOFError):
                print("\n[+] Interruption. Fermeture...")
                break

if __name__ == "__main__":
    from lyra import LyraCore

    core = LyraCore()
    cli = LyraCLI(core)
    asyncio.run(cli.start())
    