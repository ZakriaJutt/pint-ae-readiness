"""Synthetic fixtures FX-A to FX-E (execution-plan section 9). Generated, never real data.

TRNs use the documented synthetic value 100234567800003 and variants built from it.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

import openpyxl

FXA_NAME = "Al Noor Trading LLC"
CUSTOMER_HEADERS: list[object] = [
    "Customer ID", "Customer Name", "Customer Type", "TRN", "TIN", "Address", "City",
    "Country", "Emirate", "Registration Type", "Licence Number", "Licence Authority",
    "Issuing Country", "Endpoint ID",
]  # fmt: skip
ITEM_HEADERS: list[object] = [
    "Item Code", "Item Name", "Description", "Unit", "Net Price", "Gross Price",
    "Base Quantity", "Tax Category", "Tax Rate",
]  # fmt: skip
INVOICE_HEADERS: list[object] = [
    "Invoice Number", "Invoice Date", "Due Date", "Document Type", "Customer ID", "Currency",
    "Exchange Rate", "Payment Means", "Item Code", "Quantity", "Unit", "Unit Price",
    "Line Net", "Tax Category", "Tax Rate", "Invoice Net Total", "Invoice Tax Total",
    "Invoice Total", "Transaction Flags", "Credit Reason", "Preceding Invoice",
]  # fmt: skip


def synthetic_trn(i: int) -> str:
    return f"1{i:012d}03"


def xlsx_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    wb = openpyxl.Workbook()
    first = True
    for title, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        assert ws is not None
        ws.title = title
        first = False
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def csv_bytes(rows: Sequence[Sequence[object]]) -> bytes:
    import csv

    buf = io.StringIO()
    w = csv.writer(buf)
    for r in rows:
        w.writerow(["" if v is None else v for v in r])
    return buf.getvalue().encode()


def fx_a_customers() -> list[list[object]]:
    rows: list[list[object]] = [CUSTOMER_HEADERS]
    for i in range(1, 41):
        cls = "uae_business"
        trn: str | None = synthetic_trn(i)
        emirate = "DXB"
        if 1 <= i <= 6:
            trn = None  # 6 buyers without TRN or TIN
        if 7 <= i <= 9:
            emirate = "Dubayy"  # 3 emirate spellings
        if 36 <= i <= 40:
            cls, trn = "consumer", None  # 5 consumer buyers
        rows.append([
            f"C{i:03d}", f"Synthetic Customer {i:03d} LLC", cls, trn, None,
            f"Unit {i}, Synthetic Street", "Dubai", "AE", emirate, "TL", f"CN-{i:07d}",
            "Dubai DET", None, None,
        ])  # fmt: skip
    return rows


def fx_a_items() -> list[list[object]]:
    rows: list[list[object]] = [ITEM_HEADERS]
    for i in range(1, 26):
        unit = "pcs" if i <= 4 else "H87"  # 4 items with unit "pcs"
        rows.append(
            [f"I{i:03d}", f"Item {i:03d}", f"Synthetic item {i:03d}", unit, 5.00, 5.00, 1, "S", 5]
        )
    return rows


def fx_a_invoices(count: int = 300) -> list[list[object]]:
    rows: list[list[object]] = [INVOICE_HEADERS]
    for i in range(1, count + 1):
        cust = f"C{(i % 35) + 1:03d}"  # business customers only, so consumer rows stay unreferenced
        qty = Decimal(i % 7 + 1)
        price = Decimal("12.50")
        net = qty * price
        tax = (net * Decimal("0.05")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total = net + tax
        number = f"INV-{i:04d}"
        if i == 300:
            number = "INV-0299"  # 1 duplicate invoice number (different date)
        if i in (10, 20):
            total += Decimal("1.00")  # 2 arithmetic mismatches
        day = f"2026-10-{(i % 28) + 1:02d}"
        rows.append([
            number, day, "2026-11-30", "380", cust, "AED", None, "30", "I010",
            str(qty), "H87", str(price), str(net), "S", "5", str(net), str(tax), str(total),
            "00000000", None, None,
        ])  # fmt: skip
    return rows


def fx_a_files() -> dict[str, tuple[str, bytes]]:
    return {
        "customers": ("customers.xlsx", xlsx_bytes({"Customers": fx_a_customers()})),
        "items": ("items.xlsx", xlsx_bytes({"Items": fx_a_items()})),
        "invoices": ("invoices.xlsx", xlsx_bytes({"Invoices": fx_a_invoices()})),
    }


def fx_c_invoices_qbo() -> bytes:
    """QuickBooks-style headers, USD invoices, 2 without exchange rate."""
    headers = [
        "Invoice No",
        "Invoice Date",
        "Due Date",
        "Customer",
        "Currency",
        "Exchange Rate",
        "Product/Service",
        "Qty",
        "Rate",
        "Amount",
        "Tax Code",
        "Tax Rate",
        "Total",
    ]
    rows: list[list[object]] = [list(headers)]
    for i in range(1, 6):
        rate = None if i <= 2 else "3.6725"
        rows.append(
            [
                f"QB-{i}",
                "2026-10-01",
                "2026-10-31",
                f"C{i:03d}",
                "USD",
                rate,
                "I001",
                "2",
                "100.00",
                "200.00",
                "S",
                "5",
                "210.00",
            ]
        )
    return csv_bytes(rows)


def fx_d_invoices_odoo() -> bytes:
    """Odoo-style export with two header rows: a title row, then the real headers."""
    rows: list[list[object]] = [
        ["Customer Invoices", None, None, None, None, None],
        ["Number", "Invoice/Bill Date", "Partner", "Untaxed Amount", "Taxes", "Total"],
        ["INV/2026/0001", "2026-10-02", "C001", "100.00", "S", "105.00"],
    ]
    return xlsx_bytes({"Sheet1": rows})


def fx_e_corrupt() -> bytes:
    return b"PK\x03\x04 this is not really a workbook"


def oversized_csv(size: int = 21 * 1024 * 1024) -> bytes:
    line = b"C001,Synthetic,uae_business\n"
    return line * (size // len(line) + 1)


def expanding_xlsx(uncompressed: int = 300 * 1024 * 1024) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        chunk = b"\0" * (1024 * 1024)
        with zf.open("xl/worksheets/sheet1.bin", "w", force_zip64=True) as fh:
            for _ in range(uncompressed // len(chunk)):
                fh.write(chunk)
    return buf.getvalue()


def external_entity_xlsx() -> bytes:
    good = xlsx_bytes({"S": [["a"], ["b"]]})
    src = zipfile.ZipFile(io.BytesIO(good))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename == "xl/workbook.xml":
                data = b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/hostname">]>' + data
            zf.writestr(info, data)
    return out.getvalue()


def macro_renamed_xlsx() -> bytes:
    good = xlsx_bytes({"S": [["a"], ["b"]]})
    src = zipfile.ZipFile(io.BytesIO(good))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for info in src.infolist():
            zf.writestr(info, src.read(info.filename))
        zf.writestr("xl/vbaProject.bin", b"\xd0\xcf\x11\xe0 synthetic macro container")
    return out.getvalue()
