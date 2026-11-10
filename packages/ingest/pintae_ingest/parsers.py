"""File checks and parsers for .xlsx and .csv (MH-04, TRD 8.5, IT-08). No web imports.

Cells are kept as text exactly as read (numbers via their shortest repr, never re-rounded),
so the rule engine can parse them with ``Decimal``. Rows keep their sheet and row number
for evidence. Header-row choice is a mapping decision, so every row is kept here.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

MAX_PREVIEW_HEADER_ROWS = 10


class RejectFile(Exception):
    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 20 * 1024 * 1024
    max_uncompressed_bytes: int = 200 * 1024 * 1024
    max_rows: int = 200_000


@dataclass(frozen=True)
class ParsedRow:
    row_number: int  # 1-based, as the user sees it in the spreadsheet
    cells: tuple[str | None, ...]


@dataclass(frozen=True)
class ParsedSheet:
    name: str | None
    rows: tuple[ParsedRow, ...]


@dataclass(frozen=True)
class ParsedFile:
    kind: str  # xlsx | csv
    sheets: tuple[ParsedSheet, ...]

    @property
    def row_count(self) -> int:
        return sum(len(s.rows) for s in self.sheets)


def cell_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        if value.time() == time(0, 0):
            return value.date().isoformat()
        return value.replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return repr(value)
    if isinstance(value, Decimal | int):
        return str(value)
    text = str(value)
    return text if text.strip() else None


_DANGEROUS_XML = re.compile(rb"<!DOCTYPE|<!ENTITY", re.IGNORECASE)


def _check_xlsx_container(data: bytes, limits: Limits) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise RejectFile("parse_failed", "The file is not a readable .xlsx workbook") from exc
    with zf:
        names = zf.namelist()
        if any(n.lower().endswith("vbaproject.bin") for n in names):
            raise RejectFile(
                "macro_content", "The workbook contains macros; save it as plain .xlsx"
            )
        total = sum(i.file_size for i in zf.infolist())
        if total > limits.max_uncompressed_bytes:
            raise RejectFile("expands_too_large", "The workbook expands beyond 200 MB when opened")
        if "[Content_Types].xml" not in names:
            raise RejectFile("parse_failed", "The file is not a readable .xlsx workbook")
        for info in zf.infolist():
            if info.filename.lower().endswith((".xml", ".rels")):
                head = zf.read(info.filename)
                if _DANGEROUS_XML.search(head):
                    raise RejectFile(
                        "external_entity", "The workbook declares XML entities, which are refused"
                    )


def _parse_xlsx(data: bytes, limits: Limits) -> ParsedFile:
    _check_xlsx_container(data, limits)
    import openpyxl  # local import keeps module import cheap for the API

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:
        raise RejectFile("parse_failed", "The workbook could not be read") from exc
    sheets: list[ParsedSheet] = []
    count = 0
    try:
        for ws in wb.worksheets:
            rows: list[ParsedRow] = []
            for idx, values in enumerate(ws.iter_rows(values_only=True), start=1):
                cells = tuple(cell_text(v) for v in values)
                if not any(c is not None for c in cells):
                    continue
                count += 1
                if count > limits.max_rows + MAX_PREVIEW_HEADER_ROWS:
                    raise RejectFile("too_many_rows", "The file has more than 200,000 rows")
                rows.append(ParsedRow(idx, cells))
            sheets.append(ParsedSheet(ws.title, tuple(rows)))
    finally:
        wb.close()
    return ParsedFile("xlsx", tuple(sheets))


def _parse_csv(data: bytes, limits: Limits) -> ParsedFile:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RejectFile("encoding", "The CSV file is not UTF-8 text") from exc
    if "\x00" in text:
        raise RejectFile("parse_failed", "The CSV file contains binary content")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows: list[ParsedRow] = []
    reader = csv.reader(io.StringIO(text, newline=""), dialect)
    try:
        for idx, values in enumerate(reader, start=1):
            cells = tuple(v if v.strip() else None for v in values)
            if not any(c is not None for c in cells):
                continue
            rows.append(ParsedRow(idx, cells))
            if len(rows) > limits.max_rows + MAX_PREVIEW_HEADER_ROWS:
                raise RejectFile("too_many_rows", "The file has more than 200,000 rows")
    except csv.Error as exc:
        raise RejectFile("parse_failed", "The CSV file could not be read") from exc
    return ParsedFile("csv", (ParsedSheet(None, tuple(rows)),))


def check_upload(original_name: str, size: int, limits: Limits) -> str:
    """Checks that run before storing: type by extension and size. Returns the kind."""
    lower = original_name.lower()
    if size > limits.max_bytes:
        raise RejectFile("too_large", "The file is larger than 20 MB")
    if size == 0:
        raise RejectFile("empty", "The file is empty")
    if lower.endswith(".xlsx"):
        return "xlsx"
    if lower.endswith(".csv"):
        return "csv"
    raise RejectFile("unsupported_type", "Only .xlsx and .csv files are accepted")


def parse(data: bytes, original_name: str, limits: Limits | None = None) -> ParsedFile:
    lim = limits or Limits()
    kind = check_upload(original_name, len(data), lim)
    parsed = _parse_xlsx(data, lim) if kind == "xlsx" else _parse_csv(data, lim)
    if parsed.row_count == 0:
        raise RejectFile("empty", "The file has no rows")
    return parsed
