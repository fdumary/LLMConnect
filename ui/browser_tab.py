import os
from dataclasses import dataclass
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import QUrl


# Data class to hold browser tab information
@dataclass
class BrowserData:
    BROWSER_MODEL_CHOICES = [
        {
            "model": "ChatGPT",
            "url": "https://chatgpt.com",
        },
        {
            "model": "Claude",
            "url": "https://claude.ai",
        },
        {
            "model": "Gemini",
            "url": "https://gemini.google.com",
        },
        {
            "model": "DeepSeek",
            "url": "https://chat.deepseek.com",
        },
    ]

    def __init__(self):
        self.name = None
        self.model = None
        self.role_id = None

    @property
    def _name(self):
        if not self.name:
            raise ValueError("Name is not set")
        return self.name.strip()

    @property
    def _model(self):
        if not self.model:
            raise ValueError("Model is not set")
        return self._model

    @property
    def _url(self):
        if not self.model:
            raise ValueError("Model is not set")
        try:
            model_entry = next(
                entry
                for entry in BrowserData.BROWSER_MODEL_CHOICES
                if entry["model"] == self.model
            )
            return model_entry["url"]
        except StopIteration:
            raise ValueError("Invalid model ID")

    @staticmethod
    def get_models():
        return [entry["model"] for entry in BrowserData.BROWSER_MODEL_CHOICES]

    @staticmethod
    def get_role_names():
        # This method read the files in the skills directory and returns the list of role names
        skills_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "skills/BROWSER")
        )
        print("Skills Directory:", skills_dir)
        role_names = []
        if os.path.exists(skills_dir) and os.path.isdir(skills_dir):
            for filename in os.listdir(skills_dir):
                if filename.endswith(".md"):
                    role_name = os.path.splitext(filename)[0]
                    role_names.append(role_name)
        return role_names

    def set_name(self, name: str):
        if not name:
            raise ValueError("Name cannot be empty")
        self.name = name.strip()

    def set_model(self, model: str):
        valid_models = BrowserData.get_models()
        if model not in valid_models:
            raise ValueError("Invalid model")
        self.model = model

    def set_role_id(self, role_id: str):
        valid_role_names = BrowserData.get_role_names()
        if role_id not in valid_role_names:
            raise ValueError("Invalid role ID")
        self.role_id = role_id


# New Tab class for Browser-based Models
class BrowserTab(QWidget):
    def __init__(self, data: BrowserData):
        super().__init__()
        self.name = data._name
        self.url = data._url

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.profile = QWebEngineProfile(self.name, self)

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.browser.page().__class__(self.profile, self.browser))

        self.layout.addWidget(self.browser)
        self.browser.setUrl(QUrl(self.url))

        self.on_chat_extracted_callback = None
