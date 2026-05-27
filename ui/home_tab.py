import json
from collections import defaultdict
from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QInputDialog, QStackedWidget, QVBoxLayout, QWidget

from engine.db import Database
from engine.secure_store import SecureApiKeyStore
from ui.pages.categories_page import CategoriesPage
from ui.pages.overview_page import OverviewPage
from ui.pages.projects_page import ProjectsPage
from ui.pages.recent_chats_page import RecentChatsPage


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
    return normalized[: limit - 1].rstrip() + "..."


def _slugify(value: str) -> str:
    slug = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif slug and slug[-1] != "-":
            slug.append("-")
    result = "".join(slug).strip("-")
    return result or "uncategorized"


def _model_avatar(name: str) -> str:
    normalized = (name or "").strip().lower()
    if "chatgpt" in normalized:
        return "🤖"
    if "claude" in normalized:
        return "🧠"
    if "gemini" in normalized:
        return "✨"
    if "deepseek" in normalized:
        return "🔎"
    return "💬"


class HomeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db = Database()
        self._last_payload_signature = None
        self.custom_categories = []
        self.custom_projects = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        self.overview_page = OverviewPage(
            on_navigate=self._navigate,
            on_add_browser_model=self._open_add_browser_model,
            on_add_api_key=self._open_add_api_key,
        )
        self.categories_page = CategoriesPage(
            on_navigate=self._navigate,
            on_add_category=self._add_category,
        )
        self.projects_page = ProjectsPage(
            on_navigate=self._navigate,
            on_add_project=self._add_project,
        )
        self.recent_page = RecentChatsPage(on_navigate=self._navigate)

        self.page_map = {
            "overview": 0,
            "categories": 1,
            "projects": 2,
            "recent": 3,
        }

        self.stack.addWidget(self.overview_page)
        self.stack.addWidget(self.categories_page)
        self.stack.addWidget(self.projects_page)
        self.stack.addWidget(self.recent_page)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._poll_dashboard_updates)
        self.refresh_timer.start(2000)

        self.refresh_dashboard()

    def _navigate(self, section: str):
        index = self.page_map.get(section, 0)
        self.stack.setCurrentIndex(index)
        self.refresh_dashboard()

    def _open_add_browser_model(self):
        if hasattr(self.main_window, "prompt_new_browser_model"):
            self.main_window.prompt_new_browser_model()

    def _open_add_api_key(self):
        if hasattr(self.main_window, "prompt_new_api_key"):
            self.main_window.prompt_new_api_key()

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if not ok or not name.strip():
            return

        description, ok = QInputDialog.getText(
            self, "Category Description", "Description:"
        )
        if not ok:
            return

        item = {
            "id": f"cat-{_slugify(name)}-{len(self.custom_categories) + 1}",
            "name": name.strip(),
            "description": description.strip(),
            "count": 0,
            "latestTitle": "-",
            "latestLabel": "-",
            "dot": "blue",
        }
        self.custom_categories.append(item)
        self.refresh_dashboard()

    def _add_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if not ok or not name.strip():
            return

        description, ok = QInputDialog.getText(
            self, "Project Description", "Description:"
        )
        if not ok:
            return

        item = {
            "id": f"proj-{_slugify(name)}-{len(self.custom_projects) + 1}",
            "name": name.strip(),
            "description": description.strip(),
            "totalChats": 0,
            "latestChat": "-",
            "lastUpdated": "-",
        }
        self.custom_projects.append(item)
        self.refresh_dashboard()

    def _build_chat_payloads(self):
        chats = self.db.get_all_chats()
        ordered_chats = sorted(
            chats,
            key=lambda chat: _parse_created_at(chat.created_at) or datetime.min,
            reverse=True,
        )

        payloads = []
        for chat in ordered_chats:
            parsed_created_at = _parse_created_at(chat.created_at)
            payloads.append(
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
                    "snippet": _snippet_from_content(chat.content),
                }
            )

        return payloads

    def _build_categories(self, chat_payloads):
        chat_groups = defaultdict(list)
        for chat in chat_payloads:
            chat_groups[chat["category"]].append(chat)

        categories = []
        for category_name, category_chats in sorted(
            chat_groups.items(), key=lambda item: len(item[1]), reverse=True
        ):
            latest_chat = category_chats[0]
            categories.append(
                {
                    "id": _slugify(category_name),
                    "slug": _slugify(category_name),
                    "name": category_name,
                    "description": (
                        f"{len(category_chats)} saved chats grouped under this category."
                    ),
                    "count": len(category_chats),
                    "latestTitle": latest_chat["title"],
                    "latestLabel": _short_date_label(latest_chat["created_at"]),
                    "dot": self._category_dot(category_name),
                }
            )

        existing_ids = {item["id"] for item in categories}
        for custom in self.custom_categories:
            if custom["id"] not in existing_ids:
                categories.append(custom)

        return categories

    def _build_projects(self, chat_payloads):
        chat_groups = defaultdict(list)
        for chat in chat_payloads:
            chat_groups[chat["category"]].append(chat)

        projects = []
        for category_name, category_chats in sorted(
            chat_groups.items(), key=lambda item: len(item[1]), reverse=True
        ):
            latest_chat = category_chats[0]
            projects.append(
                {
                    "id": _slugify(category_name),
                    "slug": _slugify(category_name),
                    "name": category_name,
                    "description": (
                        f"Project-style collection derived from {len(category_chats)} saved chats."
                    ),
                    "totalChats": len(category_chats),
                    "latestChat": latest_chat["title"],
                    "lastUpdated": _short_date_label(latest_chat["created_at"]),
                }
            )

        existing_ids = {item["id"] for item in projects}
        for custom in self.custom_projects:
            if custom["id"] not in existing_ids:
                projects.append(custom)

        return projects

    def _format_last_used(self, value):
        if isinstance(value, datetime):
            return value.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")
        if isinstance(value, str) and value.strip():
            return value
        return "Not used"

    def _build_browser_models(self):
        active_name = getattr(self.main_window, "active_browser_tab_name", None)
        models = []

        for tab_name, browser_tab in self.main_window.browser_tabs_map.items():
            model_name = getattr(browser_tab, "model_name", "Unknown")
            role_name = getattr(browser_tab, "role_name", "")
            status = "active" if tab_name == active_name else "connected"
            models.append(
                {
                    "tabName": tab_name,
                    "name": model_name,
                    "modelName": model_name,
                    "provider": "Browser Session",
                    "avatar": _model_avatar(model_name),
                    "roleName": role_name,
                    "chats": int(getattr(browser_tab, "chat_count", 0) or 0),
                    "lastUsed": self._format_last_used(
                        getattr(browser_tab, "last_used_at", None)
                    ),
                    "status": status,
                    "statusLabel": "Active" if status == "active" else "Connected",
                }
            )

        models.sort(
            key=lambda item: (item["status"] != "active", item["tabName"].lower())
        )
        return models

    def _build_api_models(self):
        api_key_store = SecureApiKeyStore()
        api_models = []

        for record in api_key_store.list_api_keys():
            model_name = record.get("model", "")
            api_name = record.get("name", "")
            model_type = record.get("type", "")
            endpoint = record.get("url", "")
            metadata = " · ".join(
                item for item in [model_name, model_type, endpoint] if item
            )
            api_models.append(
                {
                    "apiName": api_name,
                    "name": api_name,
                    "modelName": model_name,
                    "model": model_name,
                    "provider": metadata or "API Integration",
                    "avatar": "🔐",
                    "status": "connected",
                    "statusLabel": "Configured",
                    "type": model_type,
                    "roleName": record.get("role", ""),
                    "tokensUsed": int(record.get("tokensUsed", 0) or 0),
                    "lastUsed": record.get("lastUsed")
                    or record.get("updatedAt")
                    or record.get("createdAt")
                    or "Not used",
                    "maskedKey": record.get("maskedKey", ""),
                }
            )

        return api_models

    def _build_roles(self, browser_models, api_models):
        role_model_map = defaultdict(set)

        for browser in browser_models:
            role_name = (browser.get("roleName") or "").strip()
            if role_name:
                role_model_map[role_name].add(
                    browser.get("tabName") or browser.get("name")
                )

        for api in api_models:
            role_name = (api.get("roleName") or "").strip()
            if role_name:
                role_model_map[role_name].add(api.get("apiName") or api.get("name"))

        if not role_model_map:
            return [
                {
                    "name": "No role assigned",
                    "description": "Assign roles while adding browser tabs or API keys.",
                    "modelCount": 0,
                    "modelNames": [],
                    "accent": "blue",
                }
            ]

        accents = ["violet", "blue", "green", "amber", "pink", "teal"]
        sorted_roles = sorted(
            role_model_map.items(), key=lambda item: len(item[1]), reverse=True
        )

        roles = []
        for index, (role_name, models) in enumerate(sorted_roles):
            model_names = sorted(filter(None, models))
            roles.append(
                {
                    "name": role_name,
                    "description": f"Assigned to {len(model_names)} model(s)",
                    "modelCount": len(model_names),
                    "modelNames": model_names,
                    "accent": accents[index % len(accents)],
                }
            )

        return roles

    def _build_stats(
        self, total_content_size, total_chats, browser_models_count, api_count
    ):
        return [
            {
                "label": "Browser Models",
                "value": browser_models_count,
                "sublabel": "Browser models currently active",
                "badge": "Live",
            },
            {
                "label": "Total Chats",
                "value": total_chats,
                "sublabel": "Saved locally in SQLite",
                "badge": "Library",
            },
            {
                "label": "API Keys",
                "value": api_count,
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

    def _build_page_payloads(self):
        chat_payloads = self._build_chat_payloads()
        categories = self._build_categories(chat_payloads)
        projects = self._build_projects(chat_payloads)
        browser_models = self._build_browser_models()
        api_models = self._build_api_models()
        roles = self._build_roles(browser_models, api_models)

        total_content_size = sum(len(chat["content"]) for chat in chat_payloads)
        stats = self._build_stats(
            total_content_size,
            len(chat_payloads),
            len(browser_models),
            len(api_models),
        )

        overview_payload = {
            "stats": stats,
            "browserModels": browser_models,
            "apiModels": api_models,
            "roles": roles,
            "recentChats": chat_payloads[:12],
        }

        categories_payload = {
            "categories": categories,
        }

        projects_payload = {
            "projects": projects,
        }

        recent_payload = {
            "recentChats": chat_payloads,
        }

        return {
            "overview": overview_payload,
            "categories": categories_payload,
            "projects": projects_payload,
            "recent": recent_payload,
        }

    def _payload_signature(self, payload):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _poll_dashboard_updates(self):
        payload = self._build_page_payloads()
        signature = self._payload_signature(payload)
        if signature != self._last_payload_signature:
            self.refresh_dashboard()

    def refresh_dashboard(self, force_reload=False):
        payload = self._build_page_payloads()
        self._last_payload_signature = self._payload_signature(payload)

        self.overview_page.set_payload(payload["overview"])
        self.categories_page.set_payload(payload["categories"])
        self.projects_page.set_payload(payload["projects"])
        self.recent_page.set_payload(payload["recent"])

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
