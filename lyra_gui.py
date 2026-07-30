import sys
import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QLineEdit, QPushButton,
    QTextEdit, QGroupBox, QFormLayout, QSplitter, QStatusBar, QMessageBox
)

API_BASE_URL = "http://127.0.0.1:8000"


class FetchModulesWorker(QThread):
    """Worker en arrière-plan pour récupérer la liste des modules sans bloquer l'UI."""
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            response = httpx.get(f"{API_BASE_URL}/modules", timeout=5.0)
            if response.status_code == 200:
                self.finished.emit(response.json())
            else:
                self.error.emit(f"Erreur API ({response.status_code}): {response.text}")
        except Exception as e:
            self.error.emit(f"Impossible de contacter l'API : {e}")


class RunModuleWorker(QThread):
    """Worker en arrière-plan pour exécuter un module OSINT."""
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, module_path: str, options: dict):
        super().__init__()
        self.module_path = module_path
        self.options = options

    def run(self):
        try:
            url = f"{API_BASE_URL}/modules/{self.module_path}/run"
            payload = {"options": self.options}
            response = httpx.post(url, json=payload, timeout=60.0)
            if response.status_code == 200:
                self.finished.emit(response.json())
            else:
                self.error.emit(f"Erreur d'exécution ({response.status_code}): {response.text}")
        except Exception as e:
            self.error.emit(f"Échec de la requête : {e}")


class LyraGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌌 Lyra OSINT Framework - Control Center")
        self.resize(1200, 750)
        
        self.modules_data = {}
        self.current_option_inputs = {}
        self.selected_module_path = None

        self._setup_stylesheet()
        self._init_ui()
        self.refresh_modules()

    def _setup_stylesheet(self):
        """Applique un thème sombre (Dark OSINT / Cyberpunk Soft)."""
        dark_theme = """
            QMainWindow, QWidget {
                background-color: #0f141d;
                color: #e0e6ed;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 6px;
                margin-top: 10px;
                font-weight: bold;
                color: #38bdf8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                background-color: #161e2e;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #1e293b;
            }
            QLineEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px;
                color: #f8fafc;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #0284c7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
            QTextEdit {
                background-color: #090d16;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                color: #4ade80;
            }
        """
        self.setStyleSheet(dark_theme)

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- PANNEAU GAUCHE : LISTE DES MODULES ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        lbl_modules = QLabel("📁 Modules OSINT")
        lbl_modules.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        left_layout.addWidget(lbl_modules)

        self.module_list = QListWidget()
        self.module_list.itemClicked.connect(self._on_module_selected)
        left_layout.addWidget(self.module_list)

        btn_refresh = QPushButton("🔄 Rafraîchir les modules")
        btn_refresh.clicked.connect(self.refresh_modules)
        left_layout.addWidget(btn_refresh)

        splitter.addWidget(left_widget)

        # --- PANNEAU DROIT : OPTIONS ET CONSOLE ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Groupe Options
        self.opts_group = QGroupBox("⚙️ Options du module")
        self.opts_layout = QFormLayout(self.opts_group)
        right_layout.addWidget(self.opts_group)

        # Bouton d'exécution
        self.btn_run = QPushButton("🚀 Exécuter le module")
        self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_current_module)
        right_layout.addWidget(self.btn_run)

        # Console de logs
        lbl_console = QLabel("💻 Log Console / Output JSON")
        lbl_console.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        right_layout.addWidget(lbl_console)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        right_layout.addWidget(self.console)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 850])

        # Barre de statut
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt. En attente de connexion API...")

    def log(self, message: str):
        """Ajoute une ligne dans la console GUI."""
        self.console.append(message)

    def refresh_modules(self):
        """Lance la récupération asynchrone des modules via l'API."""
        self.status_bar.showMessage("Connexion à l'API...")
        self.log("[*] Interrogation de l'API Lyra pour lister les modules...")
        self.worker_fetch = FetchModulesWorker()
        self.worker_fetch.finished.connect(self._on_modules_fetched)
        self.worker_fetch.error.connect(self._on_api_error)
        self.worker_fetch.start()

    def _on_modules_fetched(self, data: dict):
        self.module_list.clear()
        self.modules_data = {m["name"]: m for m in data.get("modules", [])}
        
        for mod_path in sorted(self.modules_data.keys()):
            item = QListWidgetItem(mod_path)
            self.module_list.addItem(item)
            
The tool outputs truncated. I'll proceed to commit the change for lyra_gui.py with improved parsing. I'll include the rest of the file content in the commit.