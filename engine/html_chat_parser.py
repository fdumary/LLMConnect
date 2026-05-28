from __future__ import annotations

import re
from html.parser import HTMLParser


class _MessageNode:
    def __init__(self, tag: str, attrs: dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.text_parts: list[str] = []
        self.images: list[dict[str, str]] = []


class ChatHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.messages: list[dict[str, object]] = []
        self._current: _MessageNode | None = None
        self._depth = 0

    @staticmethod
    def _attrs_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: (value or "") for key, value in attrs}

    @staticmethod
    def _class_tokens(attrs: dict[str, str]) -> str:
        return (attrs.get("class") or "").lower()

    def _is_candidate(self, tag: str, attrs: dict[str, str]) -> bool:
        class_tokens = self._class_tokens(attrs)
        data_testid = (attrs.get("data-testid") or "").lower()
        author_role = (
            attrs.get("data-message-author-role")
            or attrs.get("data-message-author")
            or ""
        ).lower()
        role = (attrs.get("role") or "").lower()

        if tag.lower() in {"article", "li"}:
            return True
        if author_role:
            return True
        if role == "listitem":
            return True
        if (
            "conversation-turn" in data_testid
            or "message" in data_testid
            or "response" in data_testid
        ):
            return True
        return bool(
            re.search(
                r"\b(message|conversation-turn|markdown|prose|assistant|user|query|response|model)\b",
                class_tokens,
            )
        )

    def _infer_role(self, attrs: dict[str, str]) -> str:
        explicit = (
            (
                attrs.get("data-message-author-role")
                or attrs.get("data-message-author")
                or ""
            )
            .strip()
            .lower()
        )
        if explicit:
            return explicit

        class_tokens = self._class_tokens(attrs)
        if any(token in class_tokens for token in ["assistant", "model", "response"]):
            return "assistant"
        if any(token in class_tokens for token in ["user", "query"]):
            return "user"
        return "message"

    def handle_starttag(self, tag: str, attrs):
        attrs_map = self._attrs_map(attrs)
        void_tag = tag.lower() in {
            "img",
            "br",
            "hr",
            "input",
            "meta",
            "link",
            "source",
            "track",
        }

        if self._current is None:
            if self._is_candidate(tag, attrs_map):
                self._current = _MessageNode(tag.lower(), attrs_map)
                self._depth = 1
            return

        if tag.lower() == "img":
            src = (
                attrs_map.get("src")
                or attrs_map.get("data-src")
                or attrs_map.get("data-original")
                or attrs_map.get("currentSrc")
                or ""
            ).strip()
            if src:
                self._current.images.append(
                    {
                        "src": src,
                        "alt": attrs_map.get("alt", ""),
                        "title": attrs_map.get("title", ""),
                    }
                )

        if void_tag:
            return

        self._depth += 1

    def handle_data(self, data: str):
        if self._current is not None and data:
            self._current.text_parts.append(data)

    def handle_endtag(self, tag: str):
        if self._current is None:
            return

        self._depth -= 1
        if self._depth > 0:
            return

        text = " ".join(
            part.strip() for part in self._current.text_parts if part.strip()
        )
        text = re.sub(r"\s+", " ", text).strip()
        images = self._current.images
        role = self._infer_role(self._current.attrs)

        if text or images:
            self.messages.append(
                {
                    "role": role,
                    "text": text,
                    "images": images,
                }
            )

        self._current = None
        self._depth = 0


def parse_chat_html(html: str, model_name: str, source_url: str) -> dict:
    parser = ChatHtmlParser()
    parser.feed(html or "")
    parser.close()
    return {
        "format": "llmconnect.chat.v2",
        "model": model_name,
        "sourceUrl": source_url,
        "extractedAt": __import__("datetime").datetime.now().isoformat(),
        "messages": parser.messages,
    }
