"""Deterministic rule engine (MH-06, T-3.2.1). The only rule engine (R-03).

Inputs are canonical rows produced by the mapper; outputs are one result per
(rule, record) plus field-level issues. Key properties, each covered by a test:

* every applicable rule runs on every in-scope record, whatever else failed or was
  excepted on that record (UT-14); exceptions are not an engine input at all;
* a field marked "not in this file", an unmapped column, a value without an approved
  mapping, an unknown seller-profile item and an unresolved prerequisite each give
  ``not_checked``, never ``pass`` (UT-03, UT-08, UT-11);
* document types 389 and 261 give ``manual_review`` (RC-11);
* consumer buyers are ``out_of_scope``; PRV-2 invoices are ``grace_period`` (UT-04, UT-18);
* money and quantities are ``Decimal`` with explicit rounding (UT-09);
* output order and hash are deterministic (UT-12).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from pintae_rules.calendar import Provision
from pintae_rules.packs import Rule, RulePack

PASS = "pass"  # noqa: S105 - outcome name
FAIL = "fail"
NOT_CHECKED = "not_checked"
MANUAL_REVIEW = "manual_review"
OUT_OF_SCOPE = "out_of_scope"
GRACE_PERIOD = "grace_period"

# not_checked reasons (schema.md findings.not_checked_reason)
FIELD_ABSENT = "field_absent"
COLUMN_UNMAPPED = "column_unmapped"
VALUE_UNMAPPED = "value_unmapped"
PROFILE_UNKNOWN = "profile_unknown"
PREREQUISITE_UNRESOLVED = "prerequisite_unresolved"

DATASETS = ("customers", "items", "invoices")
SELLER = "seller_profile"
CENT = Decimal("0.01")
UNKNOWN_TOKENS = frozenset({"unknown"})


# --------------------------------------------------------------------------- inputs


@dataclass(frozen=True)
class Row:
    row_number: int
    values: Mapping[str, str | None]  # canonical field -> raw cell text
    columns: Mapping[str, str] = field(default_factory=dict)  # canonical field -> source column
    sheet: str | None = None


@dataclass(frozen=True)
class DatasetInput:
    upload_id: str
    rows: Sequence[Row]
    # canonical field -> "mapped" | "absent". A field missing here is an unmapped column.
    field_status: Mapping[str, str]


@dataclass(frozen=True)
class EngineInput:
    seller: Mapping[str, str | None]  # seller profile; None or "unknown" means unknown
    datasets: Mapping[str, DatasetInput | None]
    # (kind, source value) -> target code; approved value mappings only
    value_maps: Mapping[tuple[str, str], str] = field(default_factory=dict)
    segment: str | None = None
    provisions: Sequence[Provision] = ()


# --------------------------------------------------------------------------- outputs


@dataclass(frozen=True)
class Issue:
    outcome: str  # fail | not_checked | manual_review | out_of_scope | grace_period
    field: str | None
    value: str | None = None
    reason: str | None = None  # not_checked reason
    message: str = ""
    row: Row | None = None


@dataclass(frozen=True)
class Finding:
    rule_code: str
    severity: str
    dataset: str
    record_key: str
    upload_id: str | None
    sheet: str | None
    row_number: int
    column_name: str | None
    field: str | None
    value_found: str | None
    outcome: str
    not_checked_reason: str | None
    message: str

    @property
    def fingerprint(self) -> str:
        return f"{self.rule_code}|{self.dataset}|{self.record_key}|{self.field or ''}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_code": self.rule_code,
            "severity": self.severity,
            "dataset": self.dataset,
            "record_key": self.record_key,
            "upload_id": self.upload_id,
            "sheet": self.sheet,
            "row_number": self.row_number,
            "column_name": self.column_name,
            "field": self.field,
            "value_found": self.value_found,
            "outcome": self.outcome,
            "not_checked_reason": self.not_checked_reason,
            "message": self.message,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class RuleResult:
    rule_code: str
    severity: str
    dataset: str
    record_key: str
    outcome: str  # pass | fail | not_checked | manual_review


@dataclass(frozen=True)
class RecordScope:
    dataset: str
    record_key: str
    scope: str  # in_scope | out_of_scope | grace_period


@dataclass(frozen=True)
class EngineResult:
    pack_code: str
    findings: tuple[Finding, ...]
    results: tuple[RuleResult, ...]
    records: tuple[RecordScope, ...]

    def outcome(self, rule_code: str, record_key: str, dataset: str | None = None) -> str | None:
        def ds_ok(name: str) -> bool:
            return dataset is None or name == dataset

        for r in self.results:
            if r.rule_code == rule_code and r.record_key == record_key and ds_ok(r.dataset):
                return r.outcome
        scope_outcomes = (OUT_OF_SCOPE, GRACE_PERIOD)
        for f in self.findings:
            if (
                f.rule_code == rule_code
                and f.record_key == record_key
                and f.outcome in scope_outcomes
                and ds_ok(f.dataset)
            ):
                return f.outcome
        return None

    @property
    def result_hash(self) -> str:
        payload = [f.as_dict() for f in self.findings]
        payload_r = [r.__dict__ for r in self.results]
        payload_s = [s.__dict__ for s in self.records]
        blob = json.dumps(
            {"pack": self.pack_code, "f": payload, "r": payload_r, "s": payload_s},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode()).hexdigest()


# --------------------------------------------------------------------------- context


class NotChecked(Exception):
    def __init__(self, field: str | None, reason: str, message: str = "") -> None:
        super().__init__(reason)
        self.field = field
        self.reason = reason
        self.message = message


@dataclass
class Record:
    dataset: str
    key: str
    rows: list[Row]
    upload_id: str | None
    field_status: Mapping[str, str]
    # derived facts
    buyer_class: str | None = None  # resolved code, for customers and invoices
    buyer_class_problem: str | None = None  # not_checked reason when unresolved
    document_type: str | None = None  # resolved code, invoices
    document_type_problem: str | None = None
    issue_date: date | None = None
    customer_key: str | None = None

    @property
    def first(self) -> Row:
        return self.rows[0]


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    return v or None


class Ctx:
    def __init__(self, pack: RulePack, inp: EngineInput) -> None:
        self.pack = pack
        self.inp = inp
        self._shapes = {k: re.compile(v) for k, v in pack.code_shapes.items()}
        self._patterns = {k: re.compile(v) for k, v in pack.patterns.items()}

    # ---- field access
    def value(self, rec: Record, name: str, row: Row | None = None) -> str | None:
        """Cell text for a canonical field, or NotChecked when the field cannot be read."""
        if rec.dataset == SELLER:
            raw = _clean(self.inp.seller.get(name))
            if raw is None or raw.lower() in UNKNOWN_TOKENS:
                raise NotChecked(name, PROFILE_UNKNOWN, f"seller {name} is unknown")
            return raw
        status = rec.field_status.get(name)
        if status == "absent":
            raise NotChecked(name, FIELD_ABSENT, f"{name} marked not in this file")
        if status != "mapped":
            raise NotChecked(name, COLUMN_UNMAPPED, f"{name} has no mapped column")
        r = row or rec.first
        return _clean(r.values.get(name))

    def has_field(self, rec: Record, name: str) -> bool:
        if rec.dataset == SELLER:
            return True
        return rec.field_status.get(name) == "mapped"

    # ---- coded values
    def code(self, list_name: str, raw: str | None) -> tuple[str, str | None]:
        """Resolve a raw value against a pack code list.

        Returns ("ok", code) | ("missing", None) | ("invalid", raw) | ("unmapped", raw).
        An exact code is accepted; otherwise only an approved value mapping translates it.
        A value shaped like a code but not in the list fails; free text without an
        approved mapping is "unmapped" (not_checked), never guessed.
        """
        if raw is None:
            return ("missing", None)
        allowed = self.pack.code_lists.get(list_name, ())
        manual = self.pack.code_lists.get(f"{list_name}_manual_review", ())
        if raw in allowed or raw in manual:
            return ("ok", raw)
        kind = self.pack.value_mapping_kinds.get(list_name, list_name)
        mapped = self.inp.value_maps.get((kind, raw))
        if mapped is not None:
            if mapped in allowed or mapped in manual:
                return ("ok", mapped)
            return ("invalid", raw)
        shape = self._shapes.get(list_name)
        if shape is not None and shape.fullmatch(raw):
            return ("invalid", raw)
        return ("unmapped", raw)

    def matches(self, pattern: str, value: str) -> bool:
        return bool(self._patterns[pattern].fullmatch(value))

    def parse_date(self, raw: str) -> date | None:
        for fmt in self.pack.date_formats:
            try:
                return datetime.strptime(raw, fmt).date()  # noqa: DTZ007 - calendar date only
            except ValueError:
                continue
        return None


def parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    text = raw.replace(",", "").replace(" ", "")
    try:
        d = Decimal(text)
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def money(d: Decimal) -> Decimal:
    return d.quantize(CENT, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- evaluators

Evaluator = Callable[[Ctx, Rule, Record], list[Issue]]
EVALUATORS: dict[str, Evaluator] = {}


def evaluator(name: str) -> Callable[[Evaluator], Evaluator]:
    def deco(fn: Evaluator) -> Evaluator:
        EVALUATORS[name] = fn
        return fn

    return deco


def _need(
    ctx: Ctx, rec: Record, name: str, issues: list[Issue], row: Row | None = None
) -> str | None:
    """Read a required value; record not_checked or a missing-value failure into ``issues``."""
    try:
        v = ctx.value(rec, name, row)
    except NotChecked as nc:
        issues.append(Issue(NOT_CHECKED, nc.field, None, nc.reason, nc.message, row))
        return None
    if v is None:
        issues.append(Issue(FAIL, name, None, None, f"{name} is empty", row))
    return v


def _digits(value: str) -> str:
    return re.sub(r"\s+", "", value)


@evaluator("seller_trn")
def _seller_trn(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    v = _need(ctx, rec, "trn", issues)
    if v is not None and not ctx.matches("trn", _digits(v)):
        issues.append(
            Issue(FAIL, "trn", v, None, "TRN must be 15 digits, start with 1, end with 03")
        )
    return issues


@evaluator("seller_tin")
def _seller_tin(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    tin = _clean(ctx.inp.seller.get("tin"))
    trn = _clean(ctx.inp.seller.get("trn"))
    tin = None if tin is not None and tin.lower() in UNKNOWN_TOKENS else tin
    trn = None if trn is not None and trn.lower() in UNKNOWN_TOKENS else trn
    if tin is None and trn is None:
        return [Issue(FAIL, "tin", None, None, "Seller has neither TRN nor TIN (IBR-177-AE)")]
    if tin is not None and not ctx.matches("tin", _digits(tin)):
        return [
            Issue(FAIL, "tin", tin, None, "TIN must be 10 digits of form 1XXXXXXXXX (IBR-148-AE)")
        ]
    if tin is None and trn is not None and not ctx.matches("trn", _digits(trn)):
        return [Issue(FAIL, "trn", trn, None, "TRN must be 15 digits, start with 1, end with 03")]
    return []


def _registration(
    ctx: Ctx, rec: Record, f_type: str, f_id: str, f_auth: str, f_country: str
) -> list[Issue]:
    issues: list[Issue] = []
    rtype = _need(ctx, rec, f_type, issues)
    _need(ctx, rec, f_id, issues)
    if rtype is None:
        return issues
    status, code = ctx.code("registration_type", rtype)
    if status != "ok":
        issues.append(
            Issue(FAIL, f_type, rtype, None, "registration type must be TL, EID, PAS or CD")
        )
        return issues
    if code == "TL":
        _need(ctx, rec, f_auth, issues)
    if code == "PAS":
        _need(ctx, rec, f_country, issues)
    return issues


@evaluator("legal_registration")
def _legal_registration(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    return _registration(
        ctx, rec, "registration_type", "licence_number", "licence_authority", "passport_country"
    )


@evaluator("buyer_legal_registration")
def _buyer_legal_registration(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    return _registration(
        ctx, rec, "legal_reg_type", "legal_reg_id", "legal_reg_authority", "legal_reg_country"
    )


def _emirate(ctx: Ctx, rec: Record, issues: list[Issue]) -> None:
    raw = _need(ctx, rec, "emirate", issues)
    if raw is None:
        return
    status, _ = ctx.code("emirate", raw)
    if status == "invalid":
        issues.append(
            Issue(FAIL, "emirate", raw, None, "emirate must be AUH, DXB, SHJ, UAQ, FUJ, AJM or RAK")
        )
    elif status == "unmapped":
        issues.append(
            Issue(
                NOT_CHECKED, "emirate", raw, VALUE_UNMAPPED, "emirate value has no approved mapping"
            )
        )


@evaluator("address")
def _address(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    if rule.param("require_name"):
        _need(ctx, rec, "name", issues)
    _need(ctx, rec, "address_line", issues)
    _need(ctx, rec, "city", issues)
    country = _need(ctx, rec, "country_code", issues)
    if country is None:
        # Emirate requirement depends on the country, which is already an issue.
        return issues
    if country.upper() == "AE":
        _emirate(ctx, rec, issues)
    return issues


@evaluator("buyer_class")
def _buyer_class(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    raw = _need(ctx, rec, "buyer_class", issues)
    if raw is None:
        return issues
    status, _ = ctx.code("buyer_class", raw)
    if status == "invalid":
        issues.append(
            Issue(FAIL, "buyer_class", raw, None, "buyer class is not a recognised class")
        )
    elif status == "unmapped":
        issues.append(
            Issue(
                NOT_CHECKED,
                "buyer_class",
                raw,
                VALUE_UNMAPPED,
                "buyer class value has no approved mapping",
            )
        )
    return issues


@evaluator("buyer_tax_id")
def _buyer_tax_id(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    # Either field may be the one the client holds; both unreadable -> not_checked.
    readable: dict[str, str | None] = {}
    problems: list[Issue] = []
    for name in ("trn", "tin"):
        try:
            readable[name] = ctx.value(rec, name)
        except NotChecked as nc:
            problems.append(Issue(NOT_CHECKED, nc.field, None, nc.reason, nc.message))
    trn, tin = readable.get("trn"), readable.get("tin")
    if trn is not None and ctx.matches("trn", _digits(trn)):
        return []
    if tin is not None and ctx.matches("tin", _digits(tin)):
        return []
    if not readable:
        # Neither identifier column can be read: we cannot say the buyer has none.
        return problems[:1]
    value = trn if trn is not None else tin
    return [
        Issue(FAIL, "trn", value, None, "UAE business buyer needs a TRN (15 digits, 1…03) or a TIN")
    ]


@evaluator("invoice_number")
def _invoice_number(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    number = _need(ctx, rec, "invoice_number", issues)
    if number is None:
        return issues
    headers = set()
    for row in rec.rows:
        headers.add(
            tuple(
                _clean(row.values.get(f)) if ctx.has_field(rec, f) else None
                for f in ("issue_date", "customer_id", "document_type")
            )
        )
    if len(headers) > 1:
        issues.append(
            Issue(
                FAIL,
                "invoice_number",
                number,
                None,
                "invoice number used for more than one invoice",
            )
        )
    return issues


@evaluator("invoice_dates")
def _invoice_dates(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    issued = _need(ctx, rec, "issue_date", issues)
    if issued is not None and ctx.parse_date(issued) is None:
        issues.append(Issue(FAIL, "issue_date", issued, None, "issue date is not a valid date"))
    _need(ctx, rec, "due_date", issues)
    return issues


@evaluator("document_type")
def _document_type(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    if rec.document_type_problem is not None:
        raw = None
        try:
            raw = ctx.value(rec, "document_type")
        except NotChecked:
            raw = None
        return [
            Issue(
                NOT_CHECKED,
                "document_type",
                raw,
                rec.document_type_problem,
                "document type cannot be derived",
            )
        ]
    manual = ctx.pack.code_lists.get("document_type_manual_review", ())
    if rec.document_type in manual:
        return [
            Issue(
                MANUAL_REVIEW,
                "document_type",
                rec.document_type,
                None,
                "self-billed or other type not assessed: Reviewer must resolve",
            )
        ]
    return []


@evaluator("currency")
def _currency(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    cur = _need(ctx, rec, "currency", issues)
    if cur is None:
        return issues
    if cur not in ctx.pack.code_lists.get("currency", ()):
        issues.append(Issue(FAIL, "currency", cur, None, "currency is not an ISO 4217 code"))
        return issues
    if cur == "AED":
        return issues
    raw = _need(ctx, rec, "exchange_rate", issues)
    if raw is None:
        return issues
    rate = parse_decimal(raw)
    max_dp = int(rule.param("max_rate_decimals", 6))
    if rate is None or rate <= 0:
        issues.append(
            Issue(FAIL, "exchange_rate", raw, None, "exchange rate is not a positive number")
        )
    else:
        exp = rate.normalize().as_tuple().exponent
        if isinstance(exp, int) and -exp > max_dp:
            issues.append(
                Issue(
                    FAIL,
                    "exchange_rate",
                    raw,
                    None,
                    f"exchange rate has more than {max_dp} decimals",
                )
            )
    return issues


@evaluator("present")
def _present(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    for name in rule.fields:
        _need(ctx, rec, name, issues)
    return issues


def _rows(rec: Record) -> list[Row]:
    return rec.rows


@evaluator("quantity_unit")
def _quantity_unit(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    for row in _rows(rec):
        if rec.dataset == "invoices":
            q = _need(ctx, rec, "quantity", issues, row)
            if q is not None and parse_decimal(q) is None:
                issues.append(Issue(FAIL, "quantity", q, None, "quantity is not a number", row))
        unit = _need(ctx, rec, "unit", issues, row)
        if unit is None:
            continue
        status, _ = ctx.code("unit", unit)
        if status == "invalid":
            issues.append(
                Issue(
                    FAIL, "unit", unit, None, "unit is not a UNECE Rec 20/21 code in this pack", row
                )
            )
        elif status == "unmapped":
            issues.append(
                Issue(
                    NOT_CHECKED,
                    "unit",
                    unit,
                    VALUE_UNMAPPED,
                    "unit value has no approved mapping",
                    row,
                )
            )
    return _dedupe(issues)


@evaluator("item_details")
def _item_details(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    for name in ("name", "description"):
        _need(ctx, rec, name, issues)
    for name in ("net_price", "gross_price", "base_quantity"):
        v = _need(ctx, rec, name, issues)
        if v is not None and parse_decimal(v) is None:
            issues.append(Issue(FAIL, name, v, None, f"{name} is not a number"))
    return issues


@evaluator("tax_category")
def _tax_category(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    no_rate = ctx.pack.code_lists.get("tax_category_without_rate", ())
    for row in _rows(rec):
        raw = _need(ctx, rec, "tax_category", issues, row)
        if raw is None:
            continue
        status, code = ctx.code("tax_category", raw)
        if status == "invalid":
            issues.append(
                Issue(FAIL, "tax_category", raw, None, "tax category is not an aligned code", row)
            )
            continue
        if status == "unmapped":
            issues.append(
                Issue(
                    NOT_CHECKED,
                    "tax_category",
                    raw,
                    VALUE_UNMAPPED,
                    "tax treatment has no approved mapping",
                    row,
                )
            )
            continue
        if code not in no_rate:
            rate = _need(ctx, rec, "tax_rate", issues, row)
            if rate is not None and parse_decimal(rate) is None:
                issues.append(Issue(FAIL, "tax_rate", rate, None, "tax rate is not a number", row))
    return _dedupe(issues)


def _dedupe(issues: list[Issue]) -> list[Issue]:
    """One issue per (field, outcome, value) for a record: findings are keyed by field."""
    seen: set[tuple[str | None, str, str | None]] = set()
    out: list[Issue] = []
    for i in issues:
        k = (i.field, i.outcome, i.value)
        if k in seen:
            continue
        seen.add(k)
        out.append(i)
    return out


@evaluator("arithmetic")
def _arithmetic(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    lines: list[tuple[Row, Decimal, Decimal, str, Decimal]] = []
    no_rate = ctx.pack.code_lists.get("tax_category_without_rate", ())
    for row in rec.rows:
        q = parse_decimal(_need(ctx, rec, "quantity", issues, row))
        p = parse_decimal(_need(ctx, rec, "unit_price", issues, row))
        n_raw = _need(ctx, rec, "line_net", issues, row)
        n = parse_decimal(n_raw)
        cat_raw = _need(ctx, rec, "tax_category", issues, row)
        cat = ctx.code("tax_category", cat_raw)[1] if cat_raw is not None else None
        rate_raw: str | None
        try:
            rate_raw = ctx.value(rec, "tax_rate", row)
        except NotChecked as nc:
            issues.append(Issue(NOT_CHECKED, nc.field, None, nc.reason, nc.message, row))
            continue
        rate = parse_decimal(rate_raw) if rate_raw is not None else None
        if rate is None:
            if cat in no_rate or cat == "Z":
                rate = Decimal(0)
            else:
                issues.append(
                    Issue(FAIL, "tax_rate", rate_raw, None, "tax rate missing for arithmetic", row)
                )
                continue
        if q is None or p is None or n is None or cat is None:
            if not any(i.row is row for i in issues):
                issues.append(
                    Issue(FAIL, "line_net", n_raw, None, "line amounts are not numbers", row)
                )
            continue
        if money(q * p) != n:
            issues.append(
                Issue(
                    FAIL,
                    "line_net",
                    n_raw,
                    None,
                    f"quantity × price = {money(q * p)}, line net {n_raw}",
                    row,
                )
            )
        lines.append((row, n, p, cat, rate))
    if any(i.outcome == NOT_CHECKED for i in issues):
        return _dedupe(issues)
    totals: dict[str, Decimal | None] = {}
    raws: dict[str, str | None] = {}
    for name in ("invoice_net_total", "invoice_tax_total", "invoice_total"):
        raws[name] = _need(ctx, rec, name, issues)
        totals[name] = parse_decimal(raws[name])
        d = totals[name]
        if raws[name] is not None and d is None:
            issues.append(Issue(FAIL, name, raws[name], None, f"{name} is not a number"))
        elif d is not None and d != d.quantize(CENT):
            issues.append(Issue(FAIL, name, raws[name], None, f"{name} has more than 2 decimals"))
    if any(i.outcome == FAIL and i.row is None for i in issues) or len(lines) != len(rec.rows):
        return _dedupe(issues)
    net_sum = sum((n for _, n, _, _, _ in lines), Decimal(0))
    by_cat: dict[tuple[str, Decimal], Decimal] = {}
    for _, n, _, cat, rate in lines:
        by_cat[(cat, rate)] = by_cat.get((cat, rate), Decimal(0)) + n
    tax_sum = sum(
        (money(base * rate / Decimal(100)) for (_, rate), base in sorted(by_cat.items())),
        Decimal(0),
    )
    net_t, tax_t, tot_t = (
        totals["invoice_net_total"],
        totals["invoice_tax_total"],
        totals["invoice_total"],
    )
    assert net_t is not None and tax_t is not None and tot_t is not None
    if money(net_sum) != net_t:
        issues.append(
            Issue(
                FAIL,
                "invoice_net_total",
                raws["invoice_net_total"],
                None,
                f"lines sum to {money(net_sum)}",
            )
        )
    if tax_sum != tax_t:
        issues.append(
            Issue(
                FAIL,
                "invoice_tax_total",
                raws["invoice_tax_total"],
                None,
                f"tax per category sums to {tax_sum}",
            )
        )
    if net_t + tax_t != tot_t:
        issues.append(
            Issue(
                FAIL, "invoice_total", raws["invoice_total"], None, f"net + tax = {net_t + tax_t}"
            )
        )
    return _dedupe(issues)


@evaluator("code_480_lines")
def _code_480_lines(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    for row in rec.rows:
        raw = _need(ctx, rec, "tax_category", issues, row)
        if raw is None:
            continue
        status, code = ctx.code("tax_category", raw)
        if status != "ok":
            issues.append(
                Issue(
                    NOT_CHECKED,
                    "tax_category",
                    raw,
                    VALUE_UNMAPPED,
                    "tax treatment not resolved",
                    row,
                )
            )
        elif code != "O":
            issues.append(
                Issue(
                    FAIL,
                    "tax_category",
                    raw,
                    None,
                    "code 480 with a line that is not out of scope",
                    row,
                )
            )
    return _dedupe(issues)


@evaluator("transaction_flags")
def _transaction_flags(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    v = _need(ctx, rec, "transaction_flags", issues)
    if v is not None and not re.fullmatch(r"[01]{8}", v):
        issues.append(
            Issue(FAIL, "transaction_flags", v, None, "transaction flags must be 8 binary flags")
        )
    return issues


@evaluator("credit_note")
def _credit_note(ctx: Ctx, rule: Rule, rec: Record) -> list[Issue]:
    issues: list[Issue] = []
    reason = _need(ctx, rec, "credit_reason", issues)
    exempt = [s.lower() for s in rule.param("no_reference_reasons", [])]
    if reason is not None and reason.lower() in exempt:
        return issues
    _need(ctx, rec, "preceding_invoice", issues)
    return issues


# --------------------------------------------------------------------------- record building


def _record_key(dataset: str, row: Row, key_field: str, field_status: Mapping[str, str]) -> str:
    if field_status.get(key_field) == "mapped":
        v = _clean(row.values.get(key_field))
        if v is not None:
            return v
    return f"row:{row.sheet or ''}:{row.row_number}"


KEY_FIELDS = {"customers": "customer_id", "items": "item_id", "invoices": "invoice_number"}


def _build_records(ds_name: str, ds: DatasetInput) -> list[Record]:
    key_field = KEY_FIELDS[ds_name]
    if ds_name != "invoices":
        recs = [
            Record(
                ds_name,
                _record_key(ds_name, r, key_field, ds.field_status),
                [r],
                ds.upload_id,
                ds.field_status,
            )
            for r in ds.rows
        ]
        # Disambiguate repeated keys deterministically so fingerprints stay unique.
        seen: dict[str, int] = {}
        for rec in recs:
            n = seen.get(rec.key, 0)
            seen[rec.key] = n + 1
            if n:
                rec.key = f"{rec.key}#{rec.first.row_number}"
        return recs
    groups: dict[str, list[Row]] = {}
    for r in ds.rows:
        groups.setdefault(_record_key(ds_name, r, key_field, ds.field_status), []).append(r)
    return [Record(ds_name, k, rows, ds.upload_id, ds.field_status) for k, rows in groups.items()]


def _resolve_buyer_class(ctx: Ctx, rec: Record) -> None:
    try:
        raw = ctx.value(rec, "buyer_class")
    except NotChecked as nc:
        rec.buyer_class_problem = nc.reason
        return
    status, code = ctx.code("buyer_class", raw)
    if status == "ok":
        rec.buyer_class = code
    elif status == "unmapped":
        rec.buyer_class_problem = VALUE_UNMAPPED
    else:
        rec.buyer_class_problem = PREREQUISITE_UNRESOLVED


def _resolve_invoice(ctx: Ctx, rec: Record, customers: Mapping[str, Record]) -> None:
    try:
        raw = ctx.value(rec, "document_type")
    except NotChecked as nc:
        rec.document_type_problem = nc.reason
        raw = None
    if rec.document_type_problem is None:
        status, code = ctx.code("document_type", raw)
        if status == "ok":
            rec.document_type = code
        else:
            rec.document_type_problem = VALUE_UNMAPPED
    try:
        issued = ctx.value(rec, "issue_date")
        rec.issue_date = ctx.parse_date(issued) if issued else None
    except NotChecked:
        rec.issue_date = None
    try:
        rec.customer_key = ctx.value(rec, "customer_id")
    except NotChecked:
        rec.customer_key = None
    cust = customers.get(rec.customer_key or "")
    if cust is not None:
        rec.buyer_class = cust.buyer_class
        rec.buyer_class_problem = cust.buyer_class_problem


# --------------------------------------------------------------------------- applicability


def _applies(
    ctx: Ctx, rule: Rule, rec: Record, commercial_buyers: set[str]
) -> tuple[bool, str | None]:
    """(applies, not_checked reason when applicability itself is unknown)."""
    a = rule.applies_to
    segs = a.get("segments")
    if segs and (ctx.inp.segment or "SEG-U") not in segs:
        return (False, None)
    if "seller_vat" in a:
        vat = _clean(ctx.inp.seller.get("vat_registered"))
        if vat is None or vat == "unknown":
            return (True, PROFILE_UNKNOWN)
        if vat not in a["seller_vat"]:
            return (False, None)
    if "buyer_class" in a and rec.dataset == "customers":
        if rec.buyer_class is None:
            return (True, rec.buyer_class_problem or PREREQUISITE_UNRESOLVED)
        if rec.buyer_class not in a["buyer_class"]:
            return (False, None)
    if "document_types" in a and rec.dataset == "invoices":
        if rec.document_type is None:
            return (True, rec.document_type_problem or VALUE_UNMAPPED)
        if rec.document_type not in a["document_types"]:
            return (False, None)
    doc_types = rule.param("document_types")
    if doc_types and rec.dataset == "customers":
        # RC-08: buyers on commercial invoices or with a UAE endpoint.
        endpoint = (
            _clean(rec.first.values.get("endpoint_id"))
            if ctx.has_field(rec, "endpoint_id")
            else None
        )
        if rec.key not in commercial_buyers and endpoint is None:
            return (False, None)
    if rec.dataset == "invoices" and rec.issue_date is not None:
        if rule.valid_from is not None and rec.issue_date < rule.valid_from:
            return (False, None)
        if rule.valid_to is not None and rec.issue_date > rule.valid_to:
            return (False, None)
    return (True, None)


# --------------------------------------------------------------------------- run


def _scope(ctx: Ctx, rec: Record) -> tuple[str, str | None]:
    if rec.dataset not in ("customers", "invoices"):
        return ("in_scope", None)
    if rec.buyer_class == "consumer":
        return ("out_of_scope", None)
    if rec.dataset == "invoices" and rec.buyer_class is not None and rec.issue_date is not None:
        for p in ctx.inp.provisions:
            if (
                p.effect == "exclude_from_denominator"
                and p.selector.get("buyer_class") == rec.buyer_class
                and p.covers(rec.issue_date)
            ):
                return ("grace_period", p.code)
    return ("in_scope", None)


def _finding(rule: Rule, rec: Record, issue: Issue) -> Finding:
    row = issue.row or rec.first
    column = None
    if issue.field is not None and rec.dataset != SELLER:
        column = row.columns.get(issue.field)
    return Finding(
        rule_code=rule.code,
        severity=rule.severity,
        dataset=rec.dataset,
        record_key=rec.key,
        upload_id=rec.upload_id,
        sheet=row.sheet,
        row_number=row.row_number,
        column_name=column,
        field=issue.field,
        value_found=issue.value,
        outcome=issue.outcome,
        not_checked_reason=issue.reason if issue.outcome == NOT_CHECKED else None,
        message=issue.message,
    )


def _rule_outcome(issues: Iterable[Issue]) -> str:
    outcomes = {i.outcome for i in issues}
    for o in (FAIL, MANUAL_REVIEW, NOT_CHECKED):
        if o in outcomes:
            return o
    return PASS


def run(pack: RulePack, inp: EngineInput) -> EngineResult:
    ctx = Ctx(pack, inp)
    seller = Record(SELLER, "seller", [Row(0, {})], None, {})
    customers: list[Record] = []
    by_ds: dict[str, list[Record]] = {}
    for ds_name in DATASETS:
        ds = inp.datasets.get(ds_name)
        by_ds[ds_name] = _build_records(ds_name, ds) if ds is not None else []
    customers = by_ds["customers"]
    for c in customers:
        _resolve_buyer_class(ctx, c)
    cust_index = {c.key: c for c in customers}
    commercial = set(pack.code_lists.get("commercial_document_type", ()))
    for inv in by_ds["invoices"]:
        _resolve_invoice(ctx, inv, cust_index)
    commercial_buyers = {
        inv.customer_key
        for inv in by_ds["invoices"]
        if inv.document_type in commercial and inv.customer_key
    }

    findings: list[Finding] = []
    results: list[RuleResult] = []
    scopes: list[RecordScope] = []
    all_records: list[Record] = [seller] + [r for ds in DATASETS for r in by_ds[ds]]
    scope_rule = next((r for r in pack.rules if r.evaluator == "buyer_class"), None)

    for rec in all_records:
        scope, prov = _scope(ctx, rec)
        scopes.append(RecordScope(rec.dataset, rec.key, scope))
        if scope != "in_scope":
            if scope_rule is not None:
                findings.append(
                    _finding(
                        scope_rule,
                        rec,
                        Issue(
                            OUT_OF_SCOPE if scope == "out_of_scope" else GRACE_PERIOD,
                            "buyer_class",
                            rec.buyer_class,
                            None,
                            "consumer buyer: out of scope"
                            if scope == "out_of_scope"
                            else f"grace period ({prov})",
                        ),
                    )
                )
            continue
        for rule in pack.rules:
            if rec.dataset not in rule.datasets:
                continue
            applies, unknown_reason = _applies(ctx, rule, rec, commercial_buyers)
            if not applies:
                continue
            if unknown_reason is not None:
                issues = [
                    Issue(
                        NOT_CHECKED,
                        rule.fields[0] if rule.fields else None,
                        None,
                        unknown_reason,
                        "applicability could not be determined",
                    )
                ]
            else:
                issues = EVALUATORS[rule.evaluator](ctx, rule, rec)
            results.append(
                RuleResult(rule.code, rule.severity, rec.dataset, rec.key, _rule_outcome(issues))
            )
            findings.extend(_finding(rule, rec, i) for i in issues)

    findings.sort(
        key=lambda f: (f.dataset, f.record_key, f.rule_code, f.field or "", f.row_number, f.outcome)
    )
    # Fingerprints must be unique per run: keep the first issue per fingerprint.
    unique: dict[str, Finding] = {}
    for f in findings:
        unique.setdefault(f.fingerprint, f)
    results.sort(key=lambda r: (r.dataset, r.record_key, r.rule_code))
    scopes.sort(key=lambda s: (s.dataset, s.record_key))
    return EngineResult(pack.code, tuple(unique.values()), tuple(results), tuple(scopes))
