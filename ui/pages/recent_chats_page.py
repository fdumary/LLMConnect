import json
import os

from PyQt6.QtCore import QObject, QUrl, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

RECENT_CHATS_HTML_PATH = os.path.join(os.path.dirname(__file__), "recent_chats.html")


def _escape_json_for_script(payload: str) -> str:
    return (
        payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


class RecentChatsBridge(QObject):
    def __init__(self, on_navigate):
        super().__init__()
        self.on_navigate = on_navigate

    @pyqtSlot(str)
    def navigate(self, section: str):
        self.on_navigate(section)


class RecentChatsPage(QWidget):
    def __init__(self, on_navigate):
        super().__init__()
        self._loaded = False
        self._payload = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QWebEngineView(self)
        self.channel = QWebChannel(self.browser.page())
        self.bridge = RecentChatsBridge(on_navigate)
        self.channel.registerObject("llmConnectBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        self.browser.loadFinished.connect(self._on_load_finished)
        self.layout.addWidget(self.browser)

    def _on_load_finished(self, ok):
        self._loaded = ok
        if ok and self._payload is not None:
            self._push_payload(self._payload)

    def _push_payload(self, payload):
        self.browser.page().runJavaScript(
            f"window.__PAGE_RENDER__({json.dumps(payload, ensure_ascii=False)});"
        )

    def set_payload(self, payload):
        self._payload = payload
        if not self._loaded:
            json_data = _escape_json_for_script(json.dumps(payload, ensure_ascii=False))
            with open(RECENT_CHATS_HTML_PATH, "r", encoding="utf-8") as handle:
                template = handle.read()
            html = template.replace("__APP_DATA__", json_data)
            base = QUrl.fromLocalFile(os.path.dirname(RECENT_CHATS_HTML_PATH) + os.sep)
            self.browser.setHtml(html, base)
            return

        self._push_payload(payload)
