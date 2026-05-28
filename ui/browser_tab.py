import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

from engine.html_chat_parser import parse_chat_html
from models import get_model_adapter


@dataclass
class BrowserData:
    BROWSER_MODEL_CHOICES = [
        {"model": "ChatGPT", "url": "https://chatgpt.com"},
        {"model": "Claude", "url": "https://claude.ai"},
        {"model": "Gemini", "url": "https://gemini.google.com"},
        {"model": "DeepSeek", "url": "https://chat.deepseek.com"},
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
        if model not in BrowserData.get_models():
            raise ValueError("Invalid model")
        self.model = model

    def set_role_id(self, role_id: str):
        if not role_id:
            self.role_id = ""
            return
        if role_id not in BrowserData.get_role_names():
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
        self._last_extract_signature = None

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
        os.makedirs(os.path.join(profile_dir, "cache"), exist_ok=True)
        self.profile.setPersistentStoragePath(profile_dir)
        self.profile.setCachePath(os.path.join(profile_dir, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        self.snapshot_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", ".llmconnect_data", "html_snapshots"
            )
        )
        os.makedirs(self.snapshot_dir, exist_ok=True)
        self.snapshot_path = os.path.join(
            self.snapshot_dir, f"{self._profile_folder_name(self.name)}.html"
        )

        self.browser = QWebEngineView(self)
        self.browser.setPage(self.browser.page().__class__(self.profile, self.browser))
        self.layout.addWidget(self.browser)
        self.browser.setUrl(QUrl(self.url))

        self.on_chat_extracted_callback = None
        self.browser.loadFinished.connect(self._inject_model_widget)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1200)
        self.poll_timer.timeout.connect(self._poll_extract_request)
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

        # lightweight runtime logging to help debug injection issues
        try:
            log_dir = os.path.join(os.path.dirname(__file__), "..", ".llmconnect_data")
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "inject.log"), "a", encoding="utf-8") as lf:
                lf.write(
                    f"[{datetime.now().isoformat()}] _inject_model_widget called for {self.name}\n"
                )
        except Exception:
            pass

        cfg_json = json.dumps(
            {
                "modelName": self.model_name,
                "rolePrompt": self.role_prompt,
            },
            ensure_ascii=False,
        )

        js = """
        (function() {
            var cfg = __CFG_JSON__;
            window._llmConnectExtractRequested = false;

            function findInputElement() {
                var selectors = [
                    '#prompt-textarea',
                    "textarea[placeholder*='Message']",
                    "div[contenteditable='true'][role='textbox']",
                    "div[contenteditable='true'][aria-label*='prompt' i]",
                    "div[contenteditable='true'][aria-label*='message' i]",
                    "div[contenteditable='true']",
                    'rich-textarea',
                    "div[aria-label*='Enter a prompt'][contenteditable='true']",
                    "div.ql-editor[contenteditable='true']",
                    'textarea'
                ];
                for (var i = 0; i < selectors.length; i++) {
                    var element = document.querySelector(selectors[i]);
                    if (element) return element;
                }
                return null;
            }

            function setInputText(text) {
                var input = findInputElement();
                if (!input) return false;
                if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
                    input.value = text;
                } else {
                    input.textContent = text;
                }
                input.dispatchEvent(new Event('input', { bubbles: true }));
                return true;
            }

            function injectRolePrompt() {
                if (!cfg.rolePrompt) return false;
                var currentInput = findInputElement();
                if (!currentInput) return false;
                var existingText = (currentInput.value || currentInput.textContent || '').trim();
                if (existingText.indexOf('[System Prompt]') === 0) return true;
                return setInputText('[System Prompt]\\n' + cfg.rolePrompt + '\\n\\n' + existingText);
            }

            if (!document.getElementById('llmconnect-widget')) {
                var style = document.createElement('style');
                style.textContent = [
                    "#llmconnect-widget { position: fixed; bottom: 20px; left: 20px; width: 280px; padding: 14px; border-radius: 14px; border: 1px solid #2a2a2a; background: rgba(16, 16, 16, 0.94); color: #f5f5f5; z-index: 2147483647; font-family: Inter, 'Segoe UI', sans-serif; }",
                    '#llmconnect-widget .title { font-size: 12px; color: #a3a3a3; margin-bottom: 10px; letter-spacing: 0.08em; text-transform: uppercase; }',
                    '#llmconnect-widget .row { display: flex; gap: 8px; }',
                    '#llmconnect-widget button { flex: 1; min-height: 34px; border-radius: 9px; border: 1px solid #2f2f2f; cursor: pointer; background: #1a1a1a; color: #f5f5f5; font-weight: 600; }',
                    '#llmconnect-widget button.primary { background: #f1f1f1; color: #0e0e0e; border-color: #f1f1f1; }',
                ].join('\\n');
                document.head.appendChild(style);

                var widget = document.createElement('div');
                widget.id = 'llmconnect-widget';

                var title = document.createElement('div');
                title.className = 'title';
                title.textContent = cfg.modelName + ' Tools';
                widget.appendChild(title);

                var row = document.createElement('div');
                row.className = 'row';

                var roleButton = document.createElement('button');
                roleButton.id = 'llmconnect-role-btn';
                roleButton.type = 'button';
                roleButton.textContent = 'Inject Role';

                var extractButton = document.createElement('button');
                extractButton.id = 'llmconnect-extract-btn';
                extractButton.type = 'button';
                extractButton.className = 'primary';
                extractButton.textContent = 'Extract Chat';

                row.appendChild(roleButton);
                row.appendChild(extractButton);
                widget.appendChild(row);
                document.body.appendChild(widget);

                roleButton.addEventListener('click', function() {
                    var ok = false;
                    try {
                        ok = injectRolePrompt();
                    } catch (error) {
                        ok = false;
                    }
                    var btn = document.getElementById('llmconnect-role-btn');
                    if (!btn) return;
                    btn.textContent = ok ? 'Injected' : 'No Input';
                    setTimeout(function() { btn.textContent = 'Inject Role'; }, 1400);
                });

                extractButton.addEventListener('click', function() {
                    window._llmConnectExtractRequested = true;
                    var btn = document.getElementById('llmconnect-extract-btn');
                    if (!btn) return;
                    btn.textContent = 'Queued';
                    setTimeout(function() { btn.textContent = 'Extract Chat'; }, 1400);
                });
            }

            if (!window._llmConnectWidgetRetryStarted) {
                window._llmConnectWidgetRetryStarted = true;
                var retryCount = 0;
                var retryTimer = setInterval(function() {
                    retryCount += 1;
                    if (document.getElementById('llmconnect-widget')) {
                        clearInterval(retryTimer);
                        return;
                    }
                    if (retryCount > 8) {
                        clearInterval(retryTimer);
                        return;
                    }
                    try {
                        if (document.body && !document.getElementById('llmconnect-widget')) {
                            var body = document.body;
                            var widget = document.createElement('div');
                            widget.id = 'llmconnect-widget';
                            widget.style.position = 'fixed';
                            widget.style.bottom = '20px';
                            widget.style.left = '20px';
                            widget.style.zIndex = '2147483647';
                            widget.style.background = 'rgba(16,16,16,0.94)';
                            widget.style.color = '#f5f5f5';
                            widget.style.border = '1px solid #2a2a2a';
                            widget.style.borderRadius = '14px';
                            widget.style.padding = '14px';
                            widget.style.width = '280px';
                            widget.textContent = cfg.modelName + ' Tools';
                            body.appendChild(widget);
                            clearInterval(retryTimer);
                        }
                    } catch (error) {
                    }
                }, 1200);
            }

            if (cfg.rolePrompt) {
                try {
                    injectRolePrompt();
                } catch (error) {
                }
            }
        })();
        """
        js = js.replace("__CFG_JSON__", cfg_json)

        def _js_callback(result=None):
            try:
                msg = f"[{datetime.now().isoformat()}] runJavaScript completed for {self.name} result={result}\n"
                print(msg.strip())
                with open(
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        ".llmconnect_data",
                        "inject.log",
                    ),
                    "a",
                    encoding="utf-8",
                ) as lf:
                    lf.write(msg)
            except Exception:
                pass

        try:
            self.browser.page().runJavaScript(js, _js_callback)
        except Exception as exc:
            try:
                with open(
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        ".llmconnect_data",
                        "inject.log",
                    ),
                    "a",
                    encoding="utf-8",
                ) as lf:
                    lf.write(
                        f"[{datetime.now().isoformat()}] runJavaScript exception for {self.name}: {exc}\n"
                    )
            except Exception:
                pass

    def _poll_extract_request(self):
        self.browser.page().runJavaScript(
            "Boolean(window._llmConnectExtractRequested === true)",
            self._handle_extract_request_state,
        )

    def _handle_extract_request_state(self, requested):
        if not requested:
            return
        self.browser.page().toHtml(self._handle_html_snapshot)

    def _handle_html_snapshot(self, html):
        if not html:
            self.browser.page().runJavaScript(
                "window._llmConnectExtractRequested = false;"
            )
            return

        html = html.strip()
        if not html:
            self.browser.page().runJavaScript(
                "window._llmConnectExtractRequested = false;"
            )
            return

        try:
            with open(self.snapshot_path, "w", encoding="utf-8") as handle:
                handle.write(html)
        except OSError:
            pass

        parsed = parse_chat_html(html, self.model_name, self.url)
        payload_json = json.dumps(parsed, ensure_ascii=False)
        signature = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        self.browser.page().runJavaScript("window._llmConnectExtractRequested = false;")

        if signature == self._last_extract_signature:
            return
        self._last_extract_signature = signature

        if self.on_chat_extracted_callback:
            self.on_chat_extracted_callback(
                {
                    "tabName": self.name,
                    "modelName": self.model_name,
                    "roleName": self.role_name,
                    "content": payload_json,
                    "createdAt": datetime.now().isoformat(),
                    "sourceHtmlPath": self.snapshot_path,
                }
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
