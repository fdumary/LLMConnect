import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import QUrl


class BrowserTab(QWidget):
    def __init__(
        self,
        tab_id: str,
        default_url: str = "https://chatgpt.com",
        role_name: str = "",
        role_skill: str = "",
    ):
        super().__init__()
        self.tab_id = tab_id
        self.role_name = role_name.strip()
        self.role_skill = role_skill.strip()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        storage_path = os.path.abspath(os.path.join(".llmconnect_data", tab_id))
        self.profile = QWebEngineProfile(tab_id, self)
        self.profile.setPersistentStoragePath(storage_path)

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.browser.page().__class__(self.profile, self.browser))

        self.layout.addWidget(self.browser)
        self.browser.setUrl(QUrl(default_url))

        self.on_chat_extracted_callback = None


class AddModelTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QWebEngineView(self))
