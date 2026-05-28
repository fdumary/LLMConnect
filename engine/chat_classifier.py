import json
import os
import re
import urllib.parse
import urllib.request


class ChatClassifier:
    def __init__(self, ollama_client=None, api_key_store=None):
        self.ollama_client = ollama_client
        self.api_key_store = api_key_store

    def classify(self, chat_text: str) -> dict:
        prompt = self._build_prompt(chat_text)

        if getattr(self.ollama_client, "base_url", None):
            result = self._call_ollama(prompt)
            if result:
                return result

        for record in self._api_records():
            result = self._call_api_record(record, prompt)
            if result:
                return result

        return self._fallback(chat_text)

    def _build_prompt(self, chat_text: str) -> str:
        prompt_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "skills", "CATEGORIZE_OLLAMA.md"
            )
        )
        template = ""
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as handle:
                template = handle.read()
        if not template.strip():
            template = (
                "Classify the chat transcript into JSON with title, category, project, summary.\n\n"
                "Transcript:\n{chat_text}"
            )
        return template.format(chat_text=chat_text)

    def _api_records(self):
        if not self.api_key_store:
            return []
        try:
            return self.api_key_store.list_api_keys()
        except Exception:
            return []

    def _call_ollama(self, prompt: str) -> dict:
        try:
            base_url = getattr(self.ollama_client, "base_url", None)
            if not base_url:
                return {}
            payload = {
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "format": "json",
            }
            req = urllib.request.Request(
                f"{base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            parsed = self._parse_response(result.get("response", ""))
            if parsed:
                return parsed
        except Exception:
            pass
        return {}

    def _call_api_record(self, record: dict, prompt: str) -> dict:
        api_type = (record.get("type") or "").strip().lower()
        model = (record.get("model") or "").strip()
        url = (record.get("url") or "").strip().rstrip("/")
        api_key = (record.get("apiKey") or "").strip()

        try:
            if api_type in {"openai", "deepseek"}:
                return self._call_openai_compatible(url, api_key, model, prompt)
            if api_type == "anthropic":
                return self._call_anthropic(url, api_key, model, prompt)
            if api_type in {"google", "gemini"}:
                return self._call_google(url, api_key, model, prompt)
        except Exception:
            return {}

        return {}

    def _call_openai_compatible(
        self, base_url: str, api_key: str, model: str, prompt: str
    ) -> dict:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = ""
        choices = result.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or choices[0].get("text") or ""
        return self._parse_response(content)

    def _call_anthropic(
        self, base_url: str, api_key: str, model: str, prompt: str
    ) -> dict:
        payload = {
            "model": model,
            "max_tokens": 512,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            f"{base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = ""
        for item in result.get("content", []):
            if item.get("type") == "text":
                content += item.get("text", "")
        return self._parse_response(content)

    def _call_google(
        self, base_url: str, api_key: str, model: str, prompt: str
    ) -> dict:
        endpoint = f"{base_url}/v1beta/models/{urllib.parse.quote(model, safe='')}:generateContent?key={urllib.parse.quote(api_key)}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = ""
        candidates = result.get("candidates") or []
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            content = "".join(part.get("text", "") for part in parts)
        return self._parse_response(content)

    def _parse_response(self, content: str) -> dict:
        if not content:
            return {}
        match = re.search(r"\{.*\}", content, re.S)
        candidate = match.group(0) if match else content
        try:
            parsed = json.loads(candidate)
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {
            "title": (parsed.get("title") or "Untitled Chat").strip()
            or "Untitled Chat",
            "category": (parsed.get("category") or "Uncategorized").strip()
            or "Uncategorized",
            "project": (parsed.get("project") or "General").strip() or "General",
            "summary": (parsed.get("summary") or "").strip(),
        }

    def _fallback(self, chat_text: str) -> dict:
        normalized = chat_text.lower()
        if "research" in normalized or "paper" in normalized:
            category = "Research"
        elif "code" in normalized or "bug" in normalized or "api" in normalized:
            category = "Development"
        else:
            category = "General"

        project = category
        title = f"{category} Chat"
        return {"title": title, "category": category, "project": project, "summary": ""}
