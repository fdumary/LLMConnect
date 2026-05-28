import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request

from cryptography.fernet import Fernet


@dataclass
class ApiKeyRecord:
    id: str
    name: str
    model: str
    type: str
    role: str
    role_prompt: str
    api_key: str
    url: str
    created_at: str
    updated_at: str


class SecureApiKeyStore:
    def __init__(self, base_dir: str = ".llmconnect_data/secure"):
        self.base_dir = os.path.abspath(base_dir)
        self.key_path = os.path.join(self.base_dir, "vault.key")
        self.store_path = os.path.join(self.base_dir, "api_keys.enc")
        os.makedirs(self.base_dir, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as handle:
                return handle.read().strip()

        key = Fernet.generate_key()
        with open(self.key_path, "wb") as handle:
            handle.write(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key

    def _read_records(self) -> list[dict]:
        if not os.path.exists(self.store_path):
            return []

        with open(self.store_path, "rb") as handle:
            encrypted_data = handle.read().strip()

        if not encrypted_data:
            return []

        decrypted = self._fernet.decrypt(encrypted_data)
        records = json.loads(decrypted.decode("utf-8"))
        return records if isinstance(records, list) else []

    def _write_records(self, records: list[dict]) -> None:
        payload = json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")
        encrypted = self._fernet.encrypt(payload)
        with open(self.store_path, "wb") as handle:
            handle.write(encrypted)
        try:
            os.chmod(self.store_path, 0o600)
        except OSError:
            pass

    @staticmethod
    def _mask_key(api_key: str) -> str:
        cleaned = api_key.strip()
        if len(cleaned) <= 8:
            return "*" * max(4, len(cleaned))
        return f"{cleaned[:4]}...{cleaned[-4:]}"

    def validate_api_key(
        self,
        name: str,
        model: str,
        api_key: str,
        url: str = "",
        type: str = "",
    ) -> tuple[bool, str]:
        normalized_name = (name or "").strip()
        normalized_model = (model or "").strip()
        normalized_api_key = (api_key or "").strip()
        normalized_url = (url or "").strip().rstrip("/")
        normalized_type = (type or "").strip().lower()

        if not normalized_name:
            return False, "API name is required."
        if not normalized_model:
            return False, "API model is required."
        if not normalized_api_key:
            return False, "API key is required."
        if not normalized_url:
            return False, "API endpoint URL is required."

        validators = {
            "openai": self._validate_openai_compatible,
            "deepseek": self._validate_openai_compatible,
            "anthropic": self._validate_anthropic,
            "google": self._validate_google,
            "gemini": self._validate_google,
        }
        validator = validators.get(normalized_type)
        if not validator:
            return False, f"Unsupported API type: {normalized_type}."

        return validator(normalized_url, normalized_model, normalized_api_key)

    def _validate_openai_compatible(
        self, base_url: str, model: str, api_key: str
    ) -> tuple[bool, str]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "llmConnect/1.0",
        }

        request = urllib.request.Request(
            f"{base_url}/models", headers=headers, method="GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= getattr(response, "status", 200) < 300:
                    return True, f"Validated access for {model}."
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, "API key was rejected by the provider."
        except Exception:
            pass

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "temperature": 0,
            "max_tokens": 1,
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= getattr(response, "status", 200) < 300:
                    return True, f"Validated access for {model}."
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, "API key was rejected by the provider."
            return False, f"Validation failed with HTTP {exc.code}."
        except Exception as exc:
            return False, f"Validation failed: {exc}."

        return False, "Validation failed."

    def _validate_anthropic(
        self, base_url: str, model: str, api_key: str
    ) -> tuple[bool, str]:
        payload = {
            "model": model,
            "max_tokens": 1,
            "temperature": 0,
            "messages": [{"role": "user", "content": "ping"}],
        }
        request = urllib.request.Request(
            f"{base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "llmConnect/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= getattr(response, "status", 200) < 300:
                    return True, f"Validated access for {model}."
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, "API key was rejected by the provider."
            return False, f"Validation failed with HTTP {exc.code}."
        except Exception as exc:
            return False, f"Validation failed: {exc}."

        return False, "Validation failed."

    def _validate_google(
        self, base_url: str, model: str, api_key: str
    ) -> tuple[bool, str]:
        endpoint = (
            f"{base_url}/v1beta/models/"
            f"{urllib.parse.quote(model, safe='')}:generateContent?key={urllib.parse.quote(api_key)}"
        )
        payload = {
            "contents": [{"parts": [{"text": "ping"}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 1},
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "llmConnect/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if 200 <= getattr(response, "status", 200) < 300:
                    return True, f"Validated access for {model}."
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, "API key was rejected by the provider."
            return False, f"Validation failed with HTTP {exc.code}."
        except Exception as exc:
            return False, f"Validation failed: {exc}."

        return False, "Validation failed."

    def list_api_keys(self) -> list[dict]:
        records = self._read_records()
        return [
            {
                "id": record.get("id", ""),
                "name": record.get("name", ""),
                "model": record.get("model", ""),
                "type": record.get("type", ""),
                "role": record.get("role", ""),
                "rolePrompt": record.get("role_prompt", ""),
                "url": record.get("url", ""),
                "apiKey": record.get("api_key", ""),
                "maskedKey": self._mask_key(record.get("api_key", "")),
                "createdAt": record.get("created_at", ""),
                "updatedAt": record.get("updated_at", ""),
            }
            for record in records
        ]

    def save_api_key(
        self,
        name: str,
        model: str,
        api_key: str,
        url: str = "",
        type: str = "",
        role: str = "",
        role_prompt: str = "",
    ) -> dict:
        records = self._read_records()
        now = datetime.now().isoformat()
        normalized_name = name.strip().lower()
        existing_index = next(
            (
                index
                for index, record in enumerate(records)
                if record.get("name", "").strip().lower() == normalized_name
            ),
            None,
        )

        record_id = (
            records[existing_index].get("id")
            if existing_index is not None and "id" in records[existing_index]
            else str(uuid.uuid4())
        )
        created_at = (
            records[existing_index].get("created_at", now)
            if existing_index is not None
            else now
        )

        record = {
            "id": record_id,
            "name": name.strip(),
            "model": model.strip(),
            "type": type.strip(),
            "role": role.strip(),
            "role_prompt": role_prompt.strip(),
            "api_key": api_key.strip(),
            "url": url.strip(),
            "created_at": created_at,
            "updated_at": now,
        }

        if existing_index is None:
            records.append(record)
        else:
            records[existing_index] = record

        self._write_records(records)
        return {
            "id": record["id"],
            "name": record["name"],
            "model": record["model"],
            "type": record["type"],
            "role": record["role"],
            "rolePrompt": record["role_prompt"],
            "url": record["url"],
            "maskedKey": self._mask_key(record["api_key"]),
            "createdAt": record["created_at"],
            "updatedAt": record["updated_at"],
        }
