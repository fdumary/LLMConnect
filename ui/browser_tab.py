import os
import json
from dataclasses import dataclass
from datetime import datetime
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import QUrl

from models import get_model_adapter


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
        return self.model

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
        if not role_id:
            self.role_id = ""
            return
        valid_role_names = BrowserData.get_role_names()
        if role_id not in valid_role_names:
            raise ValueError("Invalid role ID")
        self.role_id = role_id

    @staticmethod
    def get_role_prompt(role_id: str) -> str:
        if not role_id:
            return ""
        role_file = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "skills/BROWSER",
                f"{role_id}.md",
            )
        )
        if not os.path.exists(role_file):
            return ""
        with open(role_file, "r", encoding="utf-8") as handle:
            return handle.read().strip()


# New Tab class for Browser-based Models
class BrowserTab(QWidget):
    def __init__(self, data: BrowserData):
        super().__init__()
        self.name = data._name
        self.model_name = data.model
        self.role_name = data.role_id or ""
        self.url = data._url
        self.role_prompt = BrowserData.get_role_prompt(self.role_name)
        self.chat_count = 0
        self.last_used_at = datetime.now()
        self.model_adapter = get_model_adapter(self.model_name)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.profile = QWebEngineProfile(self.name, self)
        profile_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".llmconnect_data",
                "webengine",
                self._profile_folder_name(self.name),
            )
        )
        os.makedirs(profile_dir, exist_ok=True)
        self.profile.setPersistentStoragePath(profile_dir)
        self.profile.setCachePath(os.path.join(profile_dir, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.browser.page().__class__(self.profile, self.browser))

        self.layout.addWidget(self.browser)
        self.browser.setUrl(QUrl(self.url))

        self.on_chat_extracted_callback = None

        self.browser.loadFinished.connect(self._inject_model_widget)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self._poll_extracted_data)
        self.poll_timer.start()

    @staticmethod
    def _profile_folder_name(tab_name: str) -> str:
        cleaned = []
        for char in tab_name.strip().lower():
            if char.isalnum():
                cleaned.append(char)
            elif not cleaned or cleaned[-1] != "_":
                cleaned.append("_")
        folder_name = "".join(cleaned).strip("_")
        return folder_name or "browser_tab"

    def _inject_model_widget(self, ok: bool):
        if not ok:
            return

        config = self.model_adapter.get_config()
        js = f"""
        (function() {{
            const cfg = {json.dumps({
                "modelName": config.model_name,
                "inputSelectors": config.input_selectors,
                "userSelectors": config.user_message_selectors,
                "assistantSelectors": config.assistant_message_selectors,
                "rolePrompt": self.role_prompt,
            }, ensure_ascii=False)};

            window._llmConnectExtractedChat = null;

            function findInputElement() {{
                for (const selector of cfg.inputSelectors) {{
                    const element = document.querySelector(selector);
                    if (element) return element;
                }}
                return null;
            }}

            function setInputText(text) {{
                const input = findInputElement();
                if (!input) return false;

                if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {{
                    input.value = text;
                }} else {{
                    input.textContent = text;
                }}

                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'End', bubbles: true }}));
                return true;
            }}

            function gatherMessages(selectors, roleLabel) {{
                const messages = [];
                for (const selector of selectors) {{
                    const nodes = document.querySelectorAll(selector);
                    for (const node of nodes) {{
                        const text = (node.innerText || node.textContent || '').trim();
                        if (text) messages.push(`\\n\\n--- ${{roleLabel}} ---\\n${{text}}`);
                    }}
                }}
                return messages;
            }}

            function extractThread() {{
                const userParts = gatherMessages(cfg.userSelectors, 'USER');
                const aiParts = gatherMessages(cfg.assistantSelectors, 'AI');

                if (!userParts.length && !aiParts.length) {{
                    const fallback = [];
                    const messageNodes = document.querySelectorAll('main article, main [data-message-author-role], main [data-message-author], main [data-testid*="conversation-turn"], main [role="listitem"], main .message, main .conversation-turn, main .markdown, main .prose');
                    for (const node of messageNodes) {{
                        const text = (node.innerText || node.textContent || '').trim();
                        if (text) fallback.push(text);
                    }}
                    return fallback.join('\\n\\n');
                }}

                return [...userParts, ...aiParts].join('');
            }}

            window.__llmconnectInjectRolePrompt = function() {{
                if (!cfg.rolePrompt) return false;
                const currentInput = findInputElement();
                if (!currentInput) return false;
                const existingText = (currentInput.value || currentInput.textContent || '').trim();
                const rolePrefix = `[System Prompt]\\n${{cfg.rolePrompt}}\\n\\n`;
                if (existingText.startsWith('[System Prompt]')) return true;
                return setInputText(rolePrefix + existingText);
            }};

            if (!document.getElementById('llmconnect-widget')) {{
                const style = document.createElement('style');
                style.textContent = `
                    #llmconnect-widget {{
                        position: fixed;
                        bottom: 20px;
                        left: 20px;
                        width: 280px;
                        padding: 14px;
                        border-radius: 14px;
                        border: 1px solid #2a2a2a;
                        background: rgba(16, 16, 16, 0.94);
                        color: #f5f5f5;
                        z-index: 2147483647;
                        font-family: Inter, 'Segoe UI', sans-serif;
                    }}
                    #llmconnect-widget .title {{ font-size: 12px; color: #a3a3a3; margin-bottom: 10px; letter-spacing: 0.08em; text-transform: uppercase; }}
                    #llmconnect-widget .row {{ display: flex; gap: 8px; }}
                    #llmconnect-widget button {{
                        flex: 1;
                        min-height: 34px;
                        border-radius: 9px;
                        border: 1px solid #2f2f2f;
                        cursor: pointer;
                        background: #1a1a1a;
                        color: #f5f5f5;
                        font-weight: 600;
                    }}
                    #llmconnect-widget button.primary {{ background: #f1f1f1; color: #0e0e0e; border-color: #f1f1f1; }}
                `;
                document.head.appendChild(style);

                const widget = document.createElement('div');
                widget.id = 'llmconnect-widget';

                const title = document.createElement('div');
                title.className = 'title';
                title.textContent = cfg.modelName + ' Tools';
                widget.appendChild(title);

                const row = document.createElement('div');
                row.className = 'row';

                const roleButton = document.createElement('button');
                roleButton.id = 'llmconnect-role-btn';
                roleButton.type = 'button';
                roleButton.textContent = 'Inject Role';

                const extractButton = document.createElement('button');
                extractButton.id = 'llmconnect-extract-btn';
                extractButton.type = 'button';
                extractButton.className = 'primary';
                extractButton.textContent = 'Extract Chat';

                row.appendChild(roleButton);
                row.appendChild(extractButton);
                widget.appendChild(row);
                document.body.appendChild(widget);

                roleButton.addEventListener('click', function() {{
                    const ok = window.__llmconnectInjectRolePrompt();
                    const btn = document.getElementById('llmconnect-role-btn');
                    if (!btn) return;
                    btn.textContent = ok ? 'Injected' : 'No Input';
                    setTimeout(function() {{ btn.textContent = 'Inject Role'; }}, 1400);
                }});

                extractButton.addEventListener('click', function() {{
                    const thread = extractThread();
                    if (!thread) return;
                    window._llmConnectExtractedChat = thread;
                    const btn = document.getElementById('llmconnect-extract-btn');
                    if (!btn) return;
                    btn.textContent = 'Extracted';
                    setTimeout(function() {{ btn.textContent = 'Extract Chat'; }}, 1400);
                }});
            }}

            if (cfg.rolePrompt) {{
                window.__llmconnectInjectRolePrompt();
            }}
        }})();
        """
        self.browser.page().runJavaScript(js)

    def _poll_extracted_data(self):
        self.browser.page().runJavaScript(
            """
            (function() {
                if (!window._llmConnectExtractedChat) return null;
                const extracted = window._llmConnectExtractedChat;
                window._llmConnectExtractedChat = null;
                return extracted;
            })();
            """,
            self._handle_extracted_data,
        )

    def _handle_extracted_data(self, data):
        if not data:
            return

        self.chat_count += 1
        self.last_used_at = datetime.now()

        if self.on_chat_extracted_callback:
            self.on_chat_extracted_callback(
                {
                    "tabName": self.name,
                    "modelName": self.model_name,
                    "roleName": self.role_name,
                    "content": data,
                    "createdAt": self.last_used_at.isoformat(),
                }
            )
