"""Deterministic column mapper (MH-05, TRD 8.9, T-3.1.2). No model.

A suggestion is only a draft. A person confirms every field as a source column or as
``absent`` ("not in this file"); nothing is checked before that. An unmapped field makes
its rules ``not_checked`` (engine), which blocks Data-ready.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pintae_ingest.parsers import MAX_PREVIEW_HEADER_ROWS, ParsedFile, ParsedRow
from pintae_rules.engine import DatasetInput, Row

ABSENT = "absent"

TARGET_FIELDS: dict[str, tuple[str, ...]] = {
    "customers": (
        "customer_id", "name", "buyer_class", "trn", "tin", "address_line", "city",
        "country_code", "emirate", "legal_reg_type", "legal_reg_id", "legal_reg_authority",
        "legal_reg_country", "endpoint_id",
    ),
    "items": (
        "item_id", "name", "description", "unit", "net_price", "gross_price", "base_quantity",
        "tax_category", "tax_rate",
    ),
    "invoices": (
        "invoice_number", "issue_date", "due_date", "document_type", "customer_id", "currency",
        "exchange_rate", "payment_means", "item_id", "quantity", "unit", "unit_price",
        "line_net", "tax_category", "tax_rate", "invoice_net_total", "invoice_tax_total",
        "invoice_total", "transaction_flags", "credit_reason", "preceding_invoice",
    ),
}  # fmt: skip

# Synonym dictionary (normalised header text). Covers generic, QuickBooks-style (FX-C)
# and Odoo-style (FX-D) exports. Order matters only for readability.
_SYN: dict[str, dict[str, tuple[str, ...]]] = {
    "customers": {
        "customer_id": (
            "customerid",
            "customercode",
            "customerno",
            "accountno",
            "id",
            "partnerref",
            "reference",
        ),
        "name": (
            "name",
            "customername",
            "customer",
            "displayname",
            "partner",
            "companyname",
            "legalname",
        ),
        "buyer_class": ("buyerclass", "customertype", "customerclass", "type", "category"),
        "trn": (
            "trn",
            "vattrn",
            "taxregistrationnumber",
            "vatnumber",
            "taxid",
            "vatregistrationnumber",
            "trnno",
        ),
        "tin": ("tin", "taxidentificationnumber"),
        "address_line": (
            "address",
            "addressline",
            "addressline1",
            "street",
            "billingaddress",
            "billingstreet",
        ),
        "city": ("city", "billingcity", "town"),
        "country_code": ("country", "countrycode", "billingcountry"),
        "emirate": ("emirate", "state", "region", "billingstate", "province"),
        "legal_reg_type": ("registrationtype", "legalregistrationtype", "idtype"),
        "legal_reg_id": (
            "licencenumber",
            "licensenumber",
            "tradelicence",
            "tradelicense",
            "registrationnumber",
            "legalregistrationid",
        ),
        "legal_reg_authority": (
            "licenceauthority",
            "licenseauthority",
            "issuingauthority",
            "authority",
        ),
        "legal_reg_country": ("passportcountry", "issuingcountry"),
        "endpoint_id": ("endpointid", "peppolid", "endpoint"),
    },
    "items": {
        "item_id": ("itemid", "itemcode", "sku", "productcode", "internalreference", "code", "id"),
        "name": ("name", "itemname", "productname", "product", "item"),
        "description": ("description", "itemdescription", "salesdescription"),
        "unit": ("unit", "uom", "unitofmeasure", "units"),
        "net_price": ("netprice", "price", "salesprice", "unitprice", "rate"),
        "gross_price": ("grossprice", "listprice"),
        "base_quantity": ("basequantity", "priceperquantity"),
        "tax_category": ("taxcategory", "vatcategory", "taxcode", "taxes", "tax", "vattreatment"),
        "tax_rate": ("taxrate", "vatrate", "taxpercent", "vatpercent"),
    },
    "invoices": {
        "invoice_number": (
            "invoicenumber",
            "invoiceno",
            "invoice",
            "number",
            "documentnumber",
            "invoiceid",
            "num",
        ),
        "issue_date": ("issuedate", "invoicedate", "date", "invoicebilldate", "documentdate"),
        "due_date": ("duedate", "paymentduedate"),
        "document_type": ("documenttype", "invoicetype", "type", "typecode", "move_type"),
        "customer_id": ("customerid", "customercode", "customer", "partner", "customername"),
        "currency": ("currency", "currencycode"),
        "exchange_rate": ("exchangerate", "rate_fx", "fxrate", "currencyrate"),
        "payment_means": ("paymentmeans", "paymentmethod", "paymentterms"),
        "item_id": ("itemid", "itemcode", "productcode", "sku", "product", "productservice"),
        "quantity": ("quantity", "qty"),
        "unit": ("unit", "uom", "unitofmeasure"),
        "unit_price": ("unitprice", "price", "rate", "salesprice"),
        "line_net": (
            "linenet",
            "amount",
            "lineamount",
            "subtotal",
            "netamount",
            "lineextensionamount",
        ),
        "tax_category": ("taxcategory", "taxcode", "vatcode", "taxes", "taxtype"),
        "tax_rate": ("taxrate", "vatrate", "taxpercent"),
        "invoice_net_total": (
            "invoicenettotal",
            "untaxedamount",
            "nettotal",
            "totalbeforetax",
            "subtotalinvoice",
        ),
        "invoice_tax_total": ("invoicetaxtotal", "taxtotal", "vattotal", "taxamount", "totalvat"),
        "invoice_total": ("invoicetotal", "total", "totalamount", "amountdue", "grandtotal"),
        "transaction_flags": ("transactionflags", "transactiontype"),
        "credit_reason": ("creditreason", "reason", "creditnotereason"),
        "preceding_invoice": (
            "precedinginvoice",
            "originalinvoice",
            "reversedentry",
            "billingreference",
        ),
    },
}


def normalise_header(text: str | None) -> str:
    return re.sub(r"[^a-z0-9_]", "", (text or "").lower())


def header_fingerprint(headers: Sequence[str | None]) -> bytes:
    joined = "\x1f".join(normalise_header(h) for h in headers)
    return hashlib.sha256(joined.encode()).digest()


@dataclass(frozen=True)
class Suggestion:
    sheet: str | None
    header_row: int
    headers: tuple[str | None, ...]
    mapping: dict[str, str | None]  # field -> header text, or None (left for the user)
    fingerprint: bytes


def _match(dataset: str, header: str | None) -> str | None:
    norm = normalise_header(header)
    if not norm:
        return None
    for field, syns in _SYN[dataset].items():
        if norm == field.replace("_", "") or norm in syns:
            return field
    return None


def _score_row(dataset: str, row: ParsedRow) -> int:
    return len({f for f in (_match(dataset, c) for c in row.cells) if f is not None})


def suggest(dataset: str, parsed: ParsedFile) -> Suggestion:
    """Pick the sheet and header row with the most dictionary matches, then map columns.

    Ties go to the earliest row, so the choice is deterministic; the user may change it.
    """
    best: tuple[int, int, int] | None = None  # (score, -sheet_index, -row_index)
    choice: tuple[int, int] = (0, 0)
    for si, sheet in enumerate(parsed.sheets):
        for ri, row in enumerate(sheet.rows[:MAX_PREVIEW_HEADER_ROWS]):
            key = (_score_row(dataset, row), -si, -ri)
            if best is None or key > best:
                best, choice = key, (si, ri)
    sheet = parsed.sheets[choice[0]]
    header = sheet.rows[choice[1]] if sheet.rows else ParsedRow(1, ())
    mapping: dict[str, str | None] = dict.fromkeys(TARGET_FIELDS[dataset])
    for cell in header.cells:
        field = _match(dataset, cell)
        if field is not None and mapping.get(field) is None:
            mapping[field] = cell
    return Suggestion(
        sheet=sheet.name,
        header_row=header.row_number,
        headers=header.cells,
        mapping=mapping,
        fingerprint=header_fingerprint(header.cells),
    )


class MappingError(ValueError):
    pass


def validate_for_confirm(
    dataset: str, mapping: Mapping[str, str | None], headers: Sequence[str | None]
) -> None:
    """Every target field must be a header of the chosen row or ``absent`` (MH-05)."""
    known = {h for h in headers if h}
    missing = [f for f in TARGET_FIELDS[dataset] if mapping.get(f) is None]
    if missing:
        raise MappingError(f"fields neither mapped nor marked not in this file: {missing}")
    unknown = [f for f, src in mapping.items() if src not in (ABSENT, None) and src not in known]
    if unknown:
        raise MappingError(f"fields mapped to a column that is not in the header row: {unknown}")
    extra = [f for f in mapping if f not in TARGET_FIELDS[dataset]]
    if extra:
        raise MappingError(f"unknown target fields: {extra}")


def apply_mapping(
    upload_id: str,
    sheet: str | None,
    header_row: int,
    headers: Sequence[str | None],
    rows: Sequence[ParsedRow],
    mapping: Mapping[str, str | None],
) -> DatasetInput:
    """Canonical rows for the engine. Fields missing from ``mapping`` stay unmapped."""
    index = {h: i for i, h in enumerate(headers) if h}
    status: dict[str, str] = {}
    cols: dict[str, int] = {}
    for field, src in mapping.items():
        if src == ABSENT:
            status[field] = ABSENT
        elif src is not None and src in index:
            status[field] = "mapped"
            cols[field] = index[src]
    out: list[Row] = []
    for r in rows:
        if r.row_number <= header_row:
            continue
        values = {f: (r.cells[i] if i < len(r.cells) else None) for f, i in cols.items()}
        out.append(Row(r.row_number, values, {f: str(headers[i]) for f, i in cols.items()}, sheet))
    return DatasetInput(upload_id=upload_id, rows=out, field_status=status)
