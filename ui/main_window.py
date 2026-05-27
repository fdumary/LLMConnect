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
        if self.active_browser_tab_name:
            tab = self.browser_tabs_map.get(self.active_browser_tab_name)
            if tab is not None:
                tab.last_used_at = datetime.now()
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

            self.browser_tabs_map[dialog.selected_name] = new_tab
            self.tabs.addTab(new_tab, dialog.selected_name)

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
