"""Generated files (B2): CSV building with formula escaping (TRD 8.5) and storage of the
result as a ``files`` row. Files are read back only through ``GET /files/{id}``."""

from __future__ import annotations

import csv
import hashlib
import io
import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy.orm import Session

from pintae_core.models import FileRow
from pintae_core.storage import ObjectStore, generated_key

_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: object) -> str:
    """A cell a spreadsheet will not execute: text starting with = + - @ (or a tab or a
    carriage return) is prefixed with an apostrophe (TRD 8.5)."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def csv_bytes(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow([safe_cell(h) for h in header])
    for r in rows:
        w.writerow([safe_cell(c) for c in r])
    return ("﻿" + buf.getvalue()).encode("utf-8")


def store_file(
    s: Session,
    store: ObjectStore,
    *,
    firm_id: uuid.UUID,
    created_by: uuid.UUID | None,
    purpose: str,
    entity_id: uuid.UUID | None,
    data: bytes,
    content_type: str,
    download_name: str,
) -> FileRow:
    key = generated_key(firm_id, purpose)
    store.put(key, data)
    row = FileRow(
        firm_id=firm_id,
        created_by=created_by,
        purpose=purpose,
        entity_id=entity_id,
        storage_key=key,
        sha256=hashlib.sha256(data).digest(),
        content_type=content_type,
        download_name=download_name,
        byte_size=len(data),
    )
    s.add(row)
    s.flush()
    return row
