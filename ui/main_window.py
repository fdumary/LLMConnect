import json
import os
from PyQt6.QtWidgets import (
    QDialog,
    QMessageBox,
    QMainWindow,
    QTabBar,
    QTabWidget,
)
from datetime import datetime

from engine.secure_store import SecureApiKeyStore
from ui.browser_tab import BrowserTab, BrowserData
from ui.components.api_dialog import ApiKeyDialog
from ui.components.browser_dialog import BrowserModelDialog
from ui.home_tab import HomeTab


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
        self._restore_browser_tabs()
        self._handle_tab_changed(self.tabs.currentIndex())
        self.home_tab.refresh_dashboard()

    def _browser_tabs_state_path(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", ".llmconnect_data")
        )
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "browser_tabs.json")

    def _save_browser_tabs(self):
        tabs = []
        for tab_name, browser_tab in self.browser_tabs_map.items():
            tabs.append(
                {
                    "name": tab_name,
                    "model": getattr(browser_tab, "model_name", ""),
                    "role_id": getattr(browser_tab, "role_name", ""),
                    "url": getattr(browser_tab, "url", ""),
                    "last_used_at": getattr(browser_tab, "last_used_at", None).isoformat()
                    if getattr(browser_tab, "last_used_at", None)
                    else "",
                }
            )

        payload = {
            "activeTab": self.active_browser_tab_name or "",
            "tabs": tabs,
        }

        with open(self._browser_tabs_state_path(), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _restore_browser_tabs(self):
        state_path = self._browser_tabs_state_path()
        if not os.path.exists(state_path):
            return

        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return

        tabs = payload.get("tabs", []) if isinstance(payload, dict) else []
        active_tab_name = payload.get("activeTab", "") if isinstance(payload, dict) else ""

        for tab_data in tabs:
            if not isinstance(tab_data, dict):
                continue

            tab_name = (tab_data.get("name") or "").strip()
            model_name = (tab_data.get("model") or "").strip()
            role_id = (tab_data.get("role_id") or "").strip()
            if not tab_name or not model_name:
                continue
            if tab_name in self.browser_tabs_map:
                continue

            try:
                data = BrowserData()
                data.set_name(tab_name)
                data.set_model(model_name)
                data.set_role_id(role_id)
            except ValueError:
                continue

            browser_tab = BrowserTab(data)
            browser_tab.on_chat_extracted_callback = self.home_tab.handle_extracted_chat
            self.browser_tabs_map[tab_name] = browser_tab
            self.tabs.addTab(browser_tab, tab_name)

        if active_tab_name in self.browser_tabs_map:
            index = self.tabs.indexOf(self.browser_tabs_map[active_tab_name])
            if index >= 0:
                self.tabs.setCurrentIndex(index)

        self.home_tab.refresh_dashboard()

    def _handle_tab_changed(self, index):
        if index <= 0:
            self.active_browser_tab_name = None
            self._save_browser_tabs()
            self.home_tab.refresh_dashboard()
            return

        tab_name = self.tabs.tabText(index)
        self.active_browser_tab_name = (
            tab_name if tab_name in self.browser_tabs_map else None
        )
        if self.active_browser_tab_name:
            tab = self.browser_tabs_map.get(self.active_browser_tab_name)
            if tab is not None:
                tab.last_used_at = datetime.now()
        self._save_browser_tabs()
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
                dialog.api_role_skill or "",
            )
            self.home_tab.refresh_dashboard()
            QMessageBox.information(
                self,
                "API key saved",
                f"Saved {saved['name']} for {saved['model']} securely on disk.",
            )

    def prompt_new_browser_model(self):
        dialog = BrowserModelDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:

            data = BrowserData()
            data.set_name(dialog.selected_name)
            data.set_model(dialog.selected_model)
            data.set_role_id(dialog.selected_role_name)

            if dialog.selected_name in self.browser_tabs_map:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Tab with name '{dialog.selected_name}' already exists.",
                )
                return

            new_tab = BrowserTab(data)
            new_tab.last_used_at = datetime.now()
            new_tab.on_chat_extracted_callback = self.home_tab.handle_extracted_chat

            self.browser_tabs_map[dialog.selected_name] = new_tab
            self.tabs.addTab(new_tab, dialog.selected_name)

            self._save_browser_tabs()

            self.home_tab.refresh_dashboard()

    def close_tab(self, index):
        if index == 0:
            return

        tab_name = self.tabs.tabText(index)
        widget = self.tabs.widget(index)

        if tab_name in self.browser_tabs_map:
            del self.browser_tabs_map[tab_name]

        if hasattr(widget, "browser"):
            try:
                page = widget.browser.page()
                widget.browser.setPage(None)
                if page is not None:
                    page.deleteLater()
            except Exception:
                pass

        widget.deleteLater()
        self.tabs.removeTab(index)
        self._save_browser_tabs()
        self.home_tab.refresh_dashboard()
