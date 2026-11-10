"""Object storage behind an interface (TRD 8.5, schema.md section 4, IT-15).

Keys start with ``firms/{firm_id}/``. The local implementation is a fake for development
and tests; a real S3-compatible store is out of B1 scope (no accounts, no keys).
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

UPLOAD_PURPOSES = {
    "customers": "source-customers",
    "items": "source-items",
    "invoices": "source-invoices",
}


def upload_key(firm_id: uuid.UUID, entity_id: uuid.UUID, dataset: str) -> str:
    """The one storage-key builder for uploads: generated, never from the file name."""
    purpose = UPLOAD_PURPOSES[dataset]
    return f"firms/{firm_id}/entities/{entity_id}/{purpose}/{uuid.uuid4()}"


def generated_key(firm_id: uuid.UUID, purpose: str) -> str:
    return f"firms/{firm_id}/generated/{purpose}/{uuid.uuid4()}"


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def writable(self) -> bool: ...


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        if ".." in key.split("/") or key.startswith("/") or not key.startswith("firms/"):
            raise ValueError("invalid storage key")
        return self.root / key

    def put(self, key: str, data: bytes) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(p)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def writable(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            probe = self.root / ".probe"
            probe.write_bytes(b"ok")
            probe.unlink()
            return True
        except OSError:
            return False


def default_store() -> ObjectStore:
    from pintae_core.config import get_settings

    return LocalObjectStore(get_settings().storage_root)
