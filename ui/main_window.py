import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMainWindow,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
)

from engine.secure_store import SecureApiKeyStore
from ui.browser_tab import BrowserTab
from ui.home_tab import HomeTab

MODEL_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "engine", "model_catalog.json"
)

BROWSER_MODEL_CHOICES = [
    {"model": "ChatGPT", "url": "https://chatgpt.com", "type": "browser"},
    {"model": "Claude", "url": "https://claude.ai", "type": "browser"},
    {"model": "Gemini", "url": "https://gemini.google.com", "type": "browser"},
    {"model": "DeepSeek", "url": "https://chat.deepseek.com", "type": "browser"},
]

API_MODEL_CHOICES = [
    {
        "model": "gpt-4o-mini",
        "url": "https://api.openai.com/v1",
        "type": "openai",
    },
    {
        "model": "gpt-4.1-mini",
        "url": "https://api.openai.com/v1",
        "type": "openai",
    },
    {
        "model": "claude-3.5-sonnet",
        "url": "https://api.anthropic.com",
        "type": "anthropic",
    },
    {
        "model": "gemini-2.0-flash",
        "url": "https://generativelanguage.googleapis.com",
        "type": "google",
    },
    {
        "model": "deepseek-chat",
        "url": "https://api.deepseek.com",
        "type": "deepseek",
    },
]

ROLE_CHOICES = [
    {"name": "None", "skill": ""},
    {
        "name": "Enterprise Architect",
        "skill": "skills/ENTERPRISE_ARCHITECT.md",
    },
    {
        "name": "Senior Developer",
        "skill": "skills/SENIOR_DEVELOPER.md",
    },
    {
        "name": "Researcher",
        "skill": "skills/RESEARCHER.md",
    },
    {
        "name": "Technical Writer",
        "skill": "skills/TECHNICAL_WRITER.md",
    },
    {
        "name": "Data Scientist",
        "skill": "skills/DATA_SCIENTIST.md",
    },
]


def _load_model_catalog() -> dict:
    fallback = {
        "browser_models": BROWSER_MODEL_CHOICES,
        "api_models": API_MODEL_CHOICES,
    }

    try:
        with open(MODEL_CATALOG_PATH, "r", encoding="utf-8") as handle:
            raw_catalog = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback

    if not isinstance(raw_catalog, dict):
        return fallback

    browser_models = raw_catalog.get("browser_models", [])
    api_models = raw_catalog.get("api_models", [])
    if not isinstance(browser_models, list) or not isinstance(api_models, list):
        return fallback

    normalized_browser_models = []
    for entry in browser_models:
        if not isinstance(entry, dict):
            continue
        model = str(entry.get("model", "")).strip()
        url = str(entry.get("url", "")).strip()
        model_type = str(entry.get("type", "browser")).strip() or "browser"
        if model and url:
            normalized_browser_models.append(
                {"model": model, "url": url, "type": model_type}
            )

    normalized_api_models = []
    for entry in api_models:
        if not isinstance(entry, dict):
            continue
        model = str(entry.get("model", "")).strip()
        url = str(entry.get("url", "")).strip()
        model_type = str(entry.get("type", "")).strip()
        if model and url:
            normalized_api_models.append(
                {"model": model, "url": url, "type": model_type}
            )

    return {
        "browser_models": normalized_browser_models or fallback["browser_models"],
        "api_models": normalized_api_models or fallback["api_models"],
    }


MODEL_CATALOG = _load_model_catalog()


class BrowserModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Browser Model")
        self.setFixedSize(420, 230)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        label = QLabel("Create a browser tab for a model")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.model_options = MODEL_CATALOG["browser_models"]
        self.model_input = QComboBox()
        self.model_input.addItems([entry["model"] for entry in self.model_options])
        self.model_input.setEditable(False)
        self.role_input = QComboBox()
        for role in ROLE_CHOICES:
            self.role_input.addItem(role["name"], role["skill"])
        self.role_input.setEditable(False)
        form.addRow("Name", self.name_input)
        form.addRow("Model", self.model_input)
        form.addRow("Role", self.role_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.selected_name = None
        self.selected_model = None
        self.selected_url = None
        self.selected_role_name = None
        self.selected_role_prompt = None

    def _accept(self):
        name = self.name_input.text().strip()
        model = self.model_input.currentText().strip()
        model_entry = next(
            (entry for entry in self.model_options if entry["model"] == model),
            None,
        )
        url = model_entry["url"] if model_entry else ""
        if not name or not model or not url:
            QMessageBox.warning(
                self,
                "Missing details",
                "Name and model are required.",
            )
            return

        self.selected_name = name
        self.selected_model = model
        self.selected_url = url
        self.selected_role_name = self.role_input.currentText().strip()
        self.selected_role_skill = self.role_input.currentData() or ""
        if not self.selected_role_skill:
            self.selected_role_name = ""
        self.accept()


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add API Key")
        self.setFixedSize(460, 320)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        label = QLabel("Save an API profile securely")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.model_options = MODEL_CATALOG["api_models"]
        self.type_options = sorted(
            {entry["type"] for entry in self.model_options if entry.get("type")}
        )
        self.type_input = QComboBox()
        self.type_input.addItems(self.type_options)
        self.model_input = QComboBox()
        self.model_input.setEditable(False)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Paste the API key here")
        self.role_input = QComboBox()
        for role in ROLE_CHOICES:
            self.role_input.addItem(role["name"], role["prompt"])
        self.role_input.setEditable(False)
        form.addRow("Name", self.name_input)
        form.addRow("Type", self.type_input)
        form.addRow("Model", self.model_input)
        form.addRow("API Key", self.key_input)
        form.addRow("Role", self.role_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.api_name = None
        self.api_model = None
        self.api_url = None
        self.api_key = None
        self.api_type = None
        self.api_role_name = None
        self.api_role_prompt = None

        self.type_input.currentIndexChanged.connect(self._sync_models_for_type)
        self.model_input.currentIndexChanged.connect(self._sync_model_details)
        self._sync_models_for_type(self.type_input.currentIndex())

    def _models_for_type(self, model_type: str) -> list[dict]:
        return [
            entry for entry in self.model_options if entry.get("type") == model_type
        ]

    def _sync_models_for_type(self, index: int):
        if index < 0 or index >= len(self.type_options):
            return

        selected_type = self.type_options[index]
        matching_models = self._models_for_type(selected_type)

        self.model_input.blockSignals(True)
        self.model_input.clear()
        self.model_input.addItems([entry["model"] for entry in matching_models])
        self.model_input.blockSignals(False)

        if matching_models:
            self.model_input.setCurrentIndex(0)
            self._sync_model_details(0)
        else:
            self.api_url = ""

    def _sync_model_details(self, index: int):
        if index < 0 or index >= len(self.model_options):
            return

        current_model_type = self.type_input.currentText().strip()
        matching_models = self._models_for_type(current_model_type)
        if index >= len(matching_models):
            return

        model_entry = matching_models[index]
        self.api_url = model_entry.get("url", "")

    def _accept(self):
        name = self.name_input.text().strip()
        model = self.model_input.currentText().strip()
        api_type = self.type_input.currentText().strip()
        model_entry = next(
            (
                entry
                for entry in self.model_options
                if entry["model"] == model and entry.get("type", "") == api_type
            ),
            None,
        )
        url = model_entry["url"] if model_entry else ""
        api_key = self.key_input.text().strip()
        if not name or not model or not url or not api_key or not api_type:
            QMessageBox.warning(
                self,
                "Missing details",
                "Name, model, type, and API key are required.",
            )
            return

        self.api_name = name
        self.api_model = model
        self.api_url = url
        self.api_key = api_key
        self.api_type = api_type
        self.api_role_name = self.role_input.currentText().strip()
        self.api_role_prompt = self.role_input.currentData() or ""
        if not self.api_role_prompt:
            self.api_role_name = ""
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("llmConnect")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        self.browser_tabs_map = {}
        self.active_browser_tab_name = None
        self.api_key_store = SecureApiKeyStore()

        self.home_tab = HomeTab(self)
        self.tabs.addTab(self.home_tab, "Dashboard")
        self.tabs.currentChanged.connect(self._handle_tab_changed)

        self.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        self.add_browser_tab("ChatGPT", "profile_chatgpt", "https://chatgpt.com")
        self.add_browser_tab("Claude", "profile_claude", "https://claude.ai")
        self._handle_tab_changed(self.tabs.currentIndex())
        self.home_tab.refresh_dashboard()

    def _handle_tab_changed(self, index):
        if index <= 0:
            self.active_browser_tab_name = None
            self.home_tab.refresh_dashboard()
            return

        tab_name = self.tabs.tabText(index)
        self.active_browser_tab_name = (
            tab_name if tab_name in self.browser_tabs_map else None
        )
        self.home_tab.refresh_dashboard()

    def prompt_new_browser_model(self):
        dialog = BrowserModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            base_name = dialog.selected_name
            selected_model = dialog.selected_model or base_name
            name = base_name
            count = 1
            while name in self.browser_tabs_map:
                count += 1
                name = f"{base_name} ({count})"

            profile_id = f"profile_{selected_model.lower()}_{count}"
            self.add_browser_tab(
                name,
                profile_id,
                dialog.selected_url,
                selected_model,
                dialog.selected_role_name or "",
                dialog.selected_role_prompt or "",
            )
            self.home_tab.refresh_dashboard()

    def prompt_new_api_key(self):
        dialog = ApiKeyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            saved = self.api_key_store.save_api_key(
                dialog.api_name,
                dialog.api_model,
                dialog.api_key,
                dialog.api_url,
                dialog.api_type,
                dialog.api_role_name or "",
                dialog.api_role_prompt or "",
            )
            self.home_tab.refresh_dashboard()
            QMessageBox.information(
                self,
                "API key saved",
                f"Saved {saved['name']} for {saved['model']} securely on disk.",
            )

    def prompt_new_tab(self):
        self.prompt_new_browser_model()

    def add_browser_tab(
        self,
        name: str,
        profile_id: str,
        url: str,
        model: str = "",
        role_name: str = "",
        role_skill: str = "",
    ):
        if name in self.browser_tabs_map:
            QMessageBox.warning(
                self, "Error", f"Tab with name '{name}' already exists."
            )
            return

        new_tab = BrowserTab(profile_id, url, role_name, role_skill)
        new_tab.model_name = model
        new_tab.role_name = role_name
        new_tab.role_skill = role_skill
        new_tab.on_chat_extracted_callback = self.home_tab.process_extracted_chat

        self.browser_tabs_map[name] = new_tab
        self.tabs.addTab(new_tab, name)
        self.home_tab.refresh_dashboard()

    def close_tab(self, index):
        if index == 0:
            return

        tab_name = self.tabs.tabText(index)
        widget = self.tabs.widget(index)

        if tab_name in self.browser_tabs_map:
            del self.browser_tabs_map[tab_name]

        widget.deleteLater()
        self.tabs.removeTab(index)
        self.home_tab.refresh_dashboard()
