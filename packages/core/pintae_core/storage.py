"""Object storage behind an interface (TRD 8.5, schema.md section 4, IT-15).

Keys start with ``firms/{firm_id}/`` and then name the source (entity or generated) and the
purpose (R-13). Two implementations: a directory fake for unit-level tests, and the S3 API
(B2), which is MinIO locally and S3 later, selected by settings. No object is public: files
reach a browser only through the authorised ``GET /files/{id}`` route.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Protocol

UPLOAD_PURPOSES = {
    "customers": "source-customers",
    "items": "source-items",
    "invoices": "source-invoices",
}


def upload_key(firm_id: uuid.UUID, entity_id: uuid.UUID, dataset: str) -> str:
    """The one storage-key builder for uploads: generated, never from the file name."""
    purpose = UPLOAD_PURPOSES[dataset]
    return f"firms/{firm_id}/entities/{entity_id}/{purpose}/{uuid.uuid4()}"


GENERATED_PURPOSES = frozenset({"report", "fix_list", "handoff", "export", "dashboard_export"})


def generated_key(firm_id: uuid.UUID, purpose: str) -> str:
    if purpose not in GENERATED_PURPOSES:
        raise ValueError("unknown generated-file purpose")
    return f"firms/{firm_id}/generated/{purpose}/{uuid.uuid4()}"


def check_key(key: str) -> str:
    """Refuse keys that are not of the generated ``firms/{uuid}/...`` shape."""
    parts = key.split("/")
    if len(parts) < 4 or parts[0] != "firms" or ".." in parts or "" in parts:
        raise ValueError("invalid storage key")
    uuid.UUID(parts[1])
    return key


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def writable(self) -> bool: ...


class LocalObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / check_key(key)

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


class S3ObjectStore:
    """The S3 API (B2): MinIO at 127.0.0.1:9000 locally. Objects are private; there are no
    public URLs and no presigned URLs are issued."""

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None,
        region: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=30,
            ),
        )

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(
            Bucket=self.bucket,
            Key=check_key(key),
            Body=data,
            ContentType="application/octet-stream",
        )

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self.bucket, Key=check_key(key))
        data: bytes = obj["Body"].read()
        return data

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=check_key(key))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self.bucket, Key=check_key(key))
            return True
        except ClientError:
            return False

    def delete_prefix(self, prefix: str) -> int:
        """Test and retention clean-up of one firm's objects; the prefix names one firm."""
        parts = prefix.rstrip("/").split("/")
        if len(parts) != 2 or parts[0] != "firms":
            raise ValueError("prefix must be firms/{firm_id}/")
        uuid.UUID(parts[1])
        prefix = f"firms/{parts[1]}/"
        n = 0
        pages = self._client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=prefix
        )
        for page in pages:
            keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if keys:
                self._client.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})
                n += len(keys)
        return n

    def writable(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


def default_store() -> ObjectStore:
    from pintae_core.config import get_settings

    cfg = get_settings()
    if cfg.storage_backend == "s3":
        assert cfg.s3_access_key_id and cfg.s3_secret_access_key
        return S3ObjectStore(
            cfg.s3_bucket,
            endpoint_url=cfg.s3_endpoint_url,
            region=cfg.s3_region,
            access_key_id=cfg.s3_access_key_id,
            secret_access_key=cfg.s3_secret_access_key,
        )
    return LocalObjectStore(cfg.storage_root)
