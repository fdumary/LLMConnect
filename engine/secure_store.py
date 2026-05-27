import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime

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
