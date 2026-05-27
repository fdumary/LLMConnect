import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QMessageBox,
    QFormLayout,
)

MODEL_CATALOG = [
    {"model": "gpt-4o-mini", "url": "https://api.openai.com/v1", "type": "openai"},
    {"model": "gpt-4.1-mini", "url": "https://api.openai.com/v1", "type": "openai"},
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
    {"model": "deepseek-chat", "url": "https://api.deepseek.com", "type": "deepseek"},
]


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
        self.model_options = MODEL_CATALOG
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
        for role in self.get_roles():
            self.role_input.addItem(role["name"], role["skill"])
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
        self.api_role_skill = None

        self.type_input.currentIndexChanged.connect(self._sync_models_for_type)
        self.model_input.currentIndexChanged.connect(self._sync_model_details)
        self._sync_models_for_type(self.type_input.currentIndex())

    def get_roles(self) -> list[dict]:
        # read the file names from the skills/API directory and return a list of dict with name and skill is actually the content of the file
        skills_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "skills", "API")
        )
        roles = []
        if os.path.exists(skills_dir) and os.path.isdir(skills_dir):
            for filename in os.listdir(skills_dir):
                if filename.endswith(".md"):
                    role_name = os.path.splitext(filename)[0]
                    skill_path = os.path.join(skills_dir, filename)
                    with open(skill_path, "r", encoding="utf-8") as handle:
                        skill_content = handle.read()
                    roles.append({"name": role_name, "skill": skill_content})
        return roles

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
        self.api_role_skill = self.role_input.currentData() or ""
        if not self.api_role_skill:
            self.api_role_name = ""
        self.accept()
