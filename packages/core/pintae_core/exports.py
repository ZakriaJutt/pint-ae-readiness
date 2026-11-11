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

_FORMULA_START = ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")
_SEPARATORS = (",", ";", "\t", "|")
_LEADING_JUNK = " \t\r\n\x0b\x0c\x00"


def _starts_formula(text: str) -> bool:
    return text.lstrip(_LEADING_JUNK).startswith(_FORMULA_START)


def safe_cell(value: object) -> str:
    """A cell no spreadsheet will execute (TRD 8.5, UT-15, B2-S06):
    - text whose first character after leading whitespace or control characters is a
      formula start (``= + - @`` and their full-width forms) gets an apostrophe in front;
    - so does every such start that follows a separator (``,`` ``;`` tab ``|``), so a
      reader that splits on another list separator never sees a formula either.
    Every cell is also quoted by ``csv_bytes``."""
    text = "" if value is None else str(value)
    if text.startswith(("\t", "\r")) or _starts_formula(text):
        text = "'" + text
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        out.append(ch)
        if ch in _SEPARATORS and _starts_formula(text[i + 1 :]):
            j = i + 1
            while j < len(text) and text[j] in _LEADING_JUNK:
                out.append(text[j])
                j += 1
            out.append("'")
            i = j
            continue
        i += 1
    return "".join(out)


def csv_bytes(header: Sequence[str], rows: Iterable[Sequence[object]]) -> bytes:
    """Every field quoted (``QUOTE_ALL``), so ``,`` and ``;`` locales read the same cells."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_ALL)
    w.writerow([safe_cell(h) for h in header])
    for r in rows:
        w.writerow([safe_cell(c) for c in r])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


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
