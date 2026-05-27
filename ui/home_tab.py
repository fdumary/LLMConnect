import json
import os
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSlot, QUrl
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from engine.db import Database, SavedChat
from engine.ollama_client import OllamaClient
from engine.secure_store import SecureApiKeyStore

# Path to the external dashboard HTML used by the QWebEngine view
DASHBOARD_HTML_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")


class DashboardBridge(QObject):
    def __init__(self, home_tab: "HomeTab"):
        super().__init__()
        self.home_tab = home_tab

    @pyqtSlot()
    def openNewChat(self):
        if hasattr(self.home_tab.main_window, "prompt_new_tab"):
            self.home_tab.main_window.prompt_new_tab()

    @pyqtSlot()
    def openAddBrowserModel(self):
        if hasattr(self.home_tab.main_window, "prompt_new_browser_model"):
            self.home_tab.main_window.prompt_new_browser_model()

    @pyqtSlot()
    def openAddApiKey(self):
        if hasattr(self.home_tab.main_window, "prompt_new_api_key"):
            self.home_tab.main_window.prompt_new_api_key()

    @pyqtSlot()
    def exportDashboard(self):
        self.home_tab.export_dashboard_data()

    @pyqtSlot()
    def openSettings(self):
        QMessageBox.information(
            self.home_tab,
            "Settings",
            "Settings are not configured yet in this build.",
        )


def _parse_created_at(created_at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(created_at)
    except ValueError:
        return None


def _format_created_label(created_at: str) -> str:
    parsed = _parse_created_at(created_at)
    if not parsed:
        return created_at
    return parsed.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")


def _short_date_label(created_at: str) -> str:
    parsed = _parse_created_at(created_at)
    if not parsed:
        return created_at
    return parsed.strftime("%b %d, %Y").lstrip("0").replace(" 0", " ")


def _snippet_from_content(content: str, limit: int = 180) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _slugify(value: str) -> str:
    slug = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif slug and slug[-1] != "-":
            slug.append("-")
    result = "".join(slug).strip("-")
    return result or "uncategorized"


def _escape_json_for_script(payload: str) -> str:
    return (
        payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


class HomeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self.ollama_client = OllamaClient()
        self.bridge = DashboardBridge(self)
        self._dashboard_loaded = False
        self._last_payload_signature = None
        self._last_rendered_payload = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView()
        self.channel = QWebChannel(self.browser.page())
        self.channel.registerObject("llmConnectBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.loadFinished.connect(self._on_dashboard_load_finished)
        self.layout.addWidget(self.browser)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._poll_dashboard_updates)
        self.refresh_timer.start(2000)

        self.refresh_dashboard()

    def _build_dashboard_payload(self):
        chats = self.db.get_all_chats()
        chat_groups = defaultdict(list)
        total_content_size = 0

        for chat in chats:
            chat_groups[chat.category].append(chat)
            total_content_size += len(chat.content)

        ordered_chats = sorted(
            chats,
            key=lambda chat: _parse_created_at(chat.created_at) or datetime.min,
            reverse=True,
        )

        chat_payloads = []
        for chat in ordered_chats:
            parsed_created_at = _parse_created_at(chat.created_at)
            chat_payloads.append(
                {
                    "id": chat.id,
                    "title": chat.title,
                    "category": chat.category,
                    "content": chat.content,
                    "created_at": chat.created_at,
                    "createdLabel": _format_created_label(chat.created_at),
                    "createdTime": (
                        parsed_created_at.strftime("%I:%M %p").lstrip("0")
                        if parsed_created_at
                        else ""
                    ),
                    "messageCount": max(1, len(chat.content.splitlines()) or 1),
                    "tags": [
                        part.strip()
                        for part in chat.category.split(" ")
                        if part.strip()
                    ],
                    "snippet": _snippet_from_content(chat.content),
                }
            )

        categories = []
        for category_name, category_chats in sorted(
            chat_groups.items(), key=lambda item: len(item[1]), reverse=True
        ):
            latest_chat = sorted(
                category_chats,
                key=lambda chat: _parse_created_at(chat.created_at) or datetime.min,
                reverse=True,
            )[0]
            categories.append(
                {
                    "slug": _slugify(category_name),
                    "name": category_name,
                    "description": (
                        f"{len(category_chats)} saved chats grouped under this category."
                    ),
                    "count": len(category_chats),
                    "latestTitle": latest_chat.title,
                    "latestLabel": _short_date_label(latest_chat.created_at),
                    "dot": self._category_dot(category_name),
                }
            )

        projects = []
        for category_name, category_chats in sorted(
            chat_groups.items(), key=lambda item: len(item[1]), reverse=True
        ):
            latest_chat = sorted(
                category_chats,
                key=lambda chat: _parse_created_at(chat.created_at) or datetime.min,
                reverse=True,
            )[0]
            projects.append(
                {
                    "slug": _slugify(category_name),
                    "name": category_name,
                    "description": (
                        f"Project-style collection derived from {len(category_chats)} saved chats."
                    ),
                    "totalChats": len(category_chats),
                    "latestChat": latest_chat.title,
                    "lastUpdated": _short_date_label(latest_chat.created_at),
                }
            )

        connected_tabs = {
            name.lower(): name for name in self.main_window.browser_tabs_map.keys()
        }
        open_tab_count = len(self.main_window.browser_tabs_map)
        active_browser_tab_name = getattr(
            self.main_window, "active_browser_tab_name", None
        )
        active_browser_tab_key = (
            active_browser_tab_name.lower() if active_browser_tab_name else None
        )
        browser_models = []
        for model_name, provider, avatar in [
            ("ChatGPT", "OpenAI", "🤖"),
            ("Claude", "Anthropic", "🧠"),
            ("Gemini", "Google", "💎"),
            ("DeepSeek", "DeepSeek", "🔍"),
        ]:
            is_connected = model_name.lower() in connected_tabs
            is_active = model_name.lower() == active_browser_tab_key
            tab_name = connected_tabs.get(model_name.lower())
            browser_tab = (
                self.main_window.browser_tabs_map.get(tab_name) if tab_name else None
            )
            browser_models.append(
                {
                    "name": model_name,
                    "provider": provider,
                    "avatar": avatar,
                    "status": (
                        "active"
                        if is_active
                        else "connected" if is_connected else "idle"
                    ),
                    "statusLabel": (
                        "Active"
                        if is_active
                        else "Connected" if is_connected else "Available"
                    ),
                    "tabName": connected_tabs.get(
                        model_name.lower(),
                        "Browser tab" if is_connected else "No tab open",
                    ),
                    "roleName": (
                        getattr(browser_tab, "role_name", "") if browser_tab else ""
                    ),
                    "lastUsed": (
                        "Focused"
                        if is_active
                        else "Live now" if is_connected else "Not connected"
                    ),
                }
            )

        api_key_store = SecureApiKeyStore()
        api_models = []
        for record in api_key_store.list_api_keys():
            api_models.append(
                {
                    "name": record["name"],
                    "model": record["model"],
                    "type": record.get("type", ""),
                    "roleName": record.get("role", ""),
                    "rolePrompt": record.get("rolePrompt", ""),
                    "url": record.get("url", ""),
                    "avatar": "🔐",
                    "status": "available",
                    "statusLabel": "Ready",
                    "maskedKey": record["maskedKey"],
                    "lastUsed": "Configured securely",
                }
            )

        roles = [
            {
                "name": "Enterprise Architect",
                "description": "Strategic system design and technology roadmaps",
                "totalChats": 45,
                "accent": "violet",
                "shortPrompt": "System strategy",
            },
            {
                "name": "Senior Developer",
                "description": "Full-stack development and code review expert",
                "totalChats": 87,
                "accent": "blue",
                "shortPrompt": "Code quality",
            },
            {
                "name": "Researcher",
                "description": "Analysis, synthesis, and evidence-based thinking",
                "totalChats": 23,
                "accent": "green",
                "shortPrompt": "Insight work",
            },
            {
                "name": "Technical Writer",
                "description": "Documentation and communication expert",
                "totalChats": 31,
                "accent": "amber",
                "shortPrompt": "Docs clarity",
            },
            {
                "name": "Data Scientist",
                "description": "ML, statistics, and decision support",
                "totalChats": 55,
                "accent": "pink",
                "shortPrompt": "Model analysis",
            },
        ]

        overview_stats = [
            {
                "label": "Browser Models",
                "value": open_tab_count,
                "sublabel": "Browser tabs currently open",
                "badge": "Live",
            },
            {
                "label": "Total Chats",
                "value": len(chats),
                "sublabel": "Saved locally in SQLite",
                "badge": "Library",
            },
            {
                "label": "API Keys",
                "value": len(api_models),
                "sublabel": "Encrypted local API profiles",
                "badge": "Live",
            },
            {
                "label": "Storage",
                "value": self._format_storage_value(total_content_size),
                "sublabel": "Approximate content footprint",
                "badge": "Local",
            },
        ]

        active_chat_id = ordered_chats[0].id if ordered_chats else None

        return {
            "defaultTab": "overview",
            "activeChatId": active_chat_id,
            "focusedCategory": categories[0]["slug"] if categories else "uncategorized",
            "focusedProject": projects[0]["slug"] if projects else "uncategorized",
            "overview": {
                "openTabs": open_tab_count,
                "browserModels": open_tab_count,
                "apiModels": len(api_models),
            },
            "stats": overview_stats,
            "browserModels": browser_models,
            "apiModels": api_models,
            "roles": roles,
            "categories": categories,
            "projects": projects,
            "chats": chat_payloads,
        }

    def _category_dot(self, category_name: str) -> str:
        normalized = category_name.lower()
        if "research" in normalized:
            return "teal"
        if "arch" in normalized:
            return "violet"
        if "doc" in normalized:
            return "amber"
        if "data" in normalized:
            return "pink"
        return "blue"

    def _format_storage_value(self, total_content_size: int) -> str:
        if total_content_size <= 0:
            return "0 KB"
        if total_content_size < 1024:
            return f"{total_content_size} B"
        if total_content_size < 1024 * 1024:
            return f"{total_content_size / 1024:.1f} KB"
        return f"{total_content_size / (1024 * 1024):.1f} MB"

    def _payload_signature(self, payload):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _push_payload_to_view(self, payload):
        self._last_rendered_payload = payload
        self._last_payload_signature = self._payload_signature(payload)
        self.browser.page().runJavaScript(
            f"window.__LLMCONNECT_RENDER__({json.dumps(payload, ensure_ascii=False)});"
        )

    def _on_dashboard_load_finished(self, ok):
        self._dashboard_loaded = ok
        if ok and self._last_rendered_payload is not None:
            self._push_payload_to_view(self._last_rendered_payload)

    def _poll_dashboard_updates(self):
        payload = self._build_dashboard_payload()
        signature = self._payload_signature(payload)
        if signature != self._last_payload_signature:
            if self._dashboard_loaded:
                self._push_payload_to_view(payload)
            else:
                self.refresh_dashboard(force_reload=True)

    def refresh_dashboard(self, force_reload=False):
        payload = self._build_dashboard_payload()
        self._last_rendered_payload = payload
        signature = self._payload_signature(payload)

        if force_reload or not self._dashboard_loaded:
            json_data = _escape_json_for_script(json.dumps(payload, ensure_ascii=False))
            try:
                with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as handle:
                    html_template = handle.read()
            except Exception:
                html_template = (
                    "<html><body><pre>Unable to load dashboard.html</pre></body></html>"
                )

            html_document = html_template.replace("__APP_DATA__", json_data)
            self._last_payload_signature = signature
            base = QUrl.fromLocalFile(os.path.dirname(DASHBOARD_HTML_PATH) + os.sep)
            self.browser.setHtml(html_document, base)
            return

        if signature != self._last_payload_signature:
            self._push_payload_to_view(payload)

    def export_dashboard_data(self):
        payload = self._build_dashboard_payload()
        export_dir = os.path.abspath(".llmconnect_data")
        os.makedirs(export_dir, exist_ok=True)
        export_path = os.path.join(export_dir, "dashboard_export.json")

        with open(export_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        QMessageBox.information(
            self,
            "Export complete",
            f"Dashboard data exported to {export_path}",
        )

    def process_extracted_chat(self, chat_text):
        if not chat_text or not chat_text.strip():
            return

        result = self.ollama_client.categorize_chat("llama3", chat_text)

        title = result.get("title", "Untitled Chat")
        category = result.get("category", "Uncategorized")

        chat = SavedChat(title=title, category=category, content=chat_text)
        self.db.save_chat(chat)

        self.refresh_dashboard()
