from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QTabWidget,
    QMessageBox,
    QTabBar,
    QDialog,
    QLabel,
    QLineEdit,
    QFormLayout,
    QDialogButtonBox,
    QComboBox,
)
from PyQt6.QtCore import Qt
from ui.browser_tab import BrowserTab
from ui.home_tab import HomeTab
from engine.secure_store import SecureApiKeyStore


BROWSER_MODEL_CHOICES = [
    ("ChatGPT", "https://chatgpt.com"),
    ("Claude", "https://claude.ai"),
    ("Gemini", "https://gemini.google.com"),
    ("DeepSeek", "https://chat.deepseek.com"),
]

API_MODEL_CHOICES = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "claude-3.5-sonnet",
    "gemini-2.0-flash",
    "deepseek-chat",
]

API_URL_CHOICES = [
    "https://api.openai.com/v1",
    "https://api.anthropic.com",
    "https://generativelanguage.googleapis.com",
    "https://api.deepseek.com",
]


class BrowserModelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Browser Model")
        self.setFixedSize(420, 220)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        label = QLabel("Create a browser tab for a model")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Browser model name")
        self.model_input = QComboBox()
        self.model_input.addItems([label for label, _ in BROWSER_MODEL_CHOICES])
        self.model_input.setEditable(True)
        self.model_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.url_input = QComboBox()
        self.url_input.addItems([url for _, url in BROWSER_MODEL_CHOICES])
        self.url_input.setEditable(True)
        self.url_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_input.currentIndexChanged.connect(self._sync_url)
        form.addRow("Name", self.name_input)
        form.addRow("Model", self.model_input)
        form.addRow("URL", self.url_input)
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

        self._sync_url(self.model_input.currentIndex())

    def _sync_url(self, index: int):
        if index < 0 or index >= len(BROWSER_MODEL_CHOICES):
            return
        _, default_url = BROWSER_MODEL_CHOICES[index]
        self.url_input.setCurrentText(default_url)

    def _accept(self):
        name = self.name_input.text().strip()
        model = self.model_input.currentText().strip()
        url = self.url_input.currentText().strip()
        if not name or not model or not url:
            QMessageBox.warning(
                self,
                "Missing details",
                "Name, model, and URL are required.",
            )
            return

        self.selected_name = name
        self.selected_model = model
        self.selected_url = url
        self.accept()


class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add API Key")
        self.setFixedSize(460, 260)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)
        label = QLabel("Save an API profile securely")
        label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile name")
        self.model_input = QComboBox()
        self.model_input.addItems(API_MODEL_CHOICES)
        self.model_input.setEditable(True)
        self.model_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.url_input = QComboBox()
        self.url_input.addItems(API_URL_CHOICES)
        self.url_input.setEditable(True)
        self.url_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Paste the API key here")
        form.addRow("Name", self.name_input)
        form.addRow("Model", self.model_input)
        form.addRow("URL", self.url_input)
        form.addRow("API Key", self.key_input)
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

    def _accept(self):
        name = self.name_input.text().strip()
        model = self.model_input.currentText().strip()
        url = self.url_input.currentText().strip()
        api_key = self.key_input.text().strip()
        if not name or not model or not url or not api_key:
            QMessageBox.warning(
                self,
                "Missing details",
                "Name, model, URL, and API key are required.",
            )
            return

        self.api_name = name
        self.api_model = model
        self.api_url = url
        self.api_key = api_key
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

        # Keep track of browser tabs mapping Name -> BrowserTab
        self.browser_tabs_map = {}
        self.active_browser_tab_name = None
        self.api_key_store = SecureApiKeyStore()

        # Setup Home Tab (Index 0, not closable)
        self.home_tab = HomeTab(self)
        self.tabs.addTab(self.home_tab, "Dashboard")
        self.tabs.currentChanged.connect(self._handle_tab_changed)

        # Disable close button on the home tab
        self.tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        # Setup default tabs
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
            self.add_browser_tab(name, profile_id, dialog.selected_url, selected_model)
            self.home_tab.refresh_dashboard()

    def prompt_new_api_key(self):
        dialog = ApiKeyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            saved = self.api_key_store.save_api_key(
                dialog.api_name,
                dialog.api_model,
                dialog.api_key,
                dialog.api_url,
            )
            self.home_tab.refresh_dashboard()
            QMessageBox.information(
                self,
                "API key saved",
                f"Saved {saved['name']} for {saved['model']} securely on disk.",
            )

    def prompt_new_tab(self):
        self.prompt_new_browser_model()

    def add_browser_tab(self, name: str, profile_id: str, url: str, model: str = ""):
        if name in self.browser_tabs_map:
            QMessageBox.warning(
                self, "Error", f"Tab with name '{name}' already exists."
            )
            return

        new_tab = BrowserTab(profile_id, url)
        new_tab.model_name = model
        new_tab.on_chat_extracted_callback = self.home_tab.process_extracted_chat

        self.browser_tabs_map[name] = new_tab
        self.tabs.addTab(new_tab, name)
        self.home_tab.refresh_dashboard()

    def close_tab(self, index):
        if index == 0:
            return  # Prevent closing home tab

        tab_name = self.tabs.tabText(index)
        widget = self.tabs.widget(index)

        if tab_name in self.browser_tabs_map:
            del self.browser_tabs_map[tab_name]

        widget.deleteLater()
        self.tabs.removeTab(index)
        self.home_tab.refresh_dashboard()
