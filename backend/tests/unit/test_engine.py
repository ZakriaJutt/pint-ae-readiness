"""Rule engine and RP-1 (UT-01 to UT-09, UT-12, UT-14, UT-18; fixture suite)."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from pintae_rules.engine import money
from pintae_rules.fixtures import run_suite
from tests.helpers import (
    GOOD_SELLER,
    cal,
    clean_case,
    customer,
    invoice_line,
    item,
    rp1,
    rp1_cases,
    run_case,
)


def seller_outcome(rule: str, **seller: str | None) -> str | None:
    case = {"seller": dict(GOOD_SELLER, **seller)}
    return run_case(case).outcome(rule, "seller")


def test_rp1_fixture_suite_passes() -> None:
    assert run_suite(rp1(), rp1_cases(), cal().provisions) == []


def test_ut01_trn_formats() -> None:
    assert seller_outcome("RC-01", trn="100234567800003") == "pass"
    assert seller_outcome("RC-01", trn="100234567800001") == "fail"
    assert seller_outcome("RC-01", trn="200234567800003") == "fail"
    assert seller_outcome("RC-01", trn="10023456780003") == "fail"
    r = run_case({"seller": dict(GOOD_SELLER, trn="1002 3456 7800 003")})
    assert r.outcome("RC-01", "seller") == "pass"
    bad = run_case({"seller": dict(GOOD_SELLER, trn="2002 3456 7800 003")})
    f = next(f for f in bad.findings if f.rule_code == "RC-01")
    assert f.value_found == "2002 3456 7800 003"  # original shown


def test_ut02_tin() -> None:
    base = {"vat_registered": "no", "trn": None}
    assert seller_outcome("RC-02", **base, tin="1002345678") == "pass"
    assert seller_outcome("RC-02", **base, tin="0002345678") == "fail"
    r = run_case({"seller": dict(GOOD_SELLER, **base, tin=None)})
    assert r.outcome("RC-02", "seller") == "fail"
    f = next(f for f in r.findings if f.rule_code == "RC-02")
    assert "IBR-177-AE" in f.message


def test_ut03_emirate_value_mapping() -> None:
    assert seller_outcome("RC-04", emirate="DXB") == "pass"
    assert seller_outcome("RC-04", emirate="DUB") == "fail"
    r = run_case({"seller": dict(GOOD_SELLER, emirate="Dubai")})
    assert r.outcome("RC-04", "seller") == "not_checked"
    f = next(f for f in r.findings if f.rule_code == "RC-04")
    assert f.not_checked_reason == "value_unmapped"
    approved = run_case(
        {"seller": dict(GOOD_SELLER, emirate="Dubai"), "value_maps": [["emirate", "Dubai", "DXB"]]}
    )
    assert approved.outcome("RC-04", "seller") == "pass"
    # Same behaviour on buyer emirates (RC-06).
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(emirate="Dubayy")]
    assert run_case(c).outcome("RC-06", "C1") == "not_checked"


def test_ut04_consumer_out_of_scope_and_out_of_denominator() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(buyer_class="consumer", trn=None)]
    r = run_case(c)
    assert r.outcome("RC-05", "C1", "customers") == "out_of_scope"
    assert r.outcome("RC-07", "C1") is None
    scope = [s for s in r.records if s.dataset == "customers"]
    assert [s.scope for s in scope] == ["out_of_scope"]


def test_ut05_business_buyer_identifier() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(trn=None)]
    assert run_case(c).outcome("RC-07", "C1") == "fail"
    c["datasets"]["customers"]["rows"] = [customer(trn="client does not know")]
    r = run_case(c)
    assert r.outcome("RC-07", "C1") == "fail"
    f = next(f for f in r.findings if f.rule_code == "RC-07")
    assert f.value_found == "client does not know"  # nothing invented
    c["datasets"]["customers"]["rows"] = [
        customer(buyer_class="foreign", trn=None, country_code="GB")
    ]
    assert run_case(c).outcome("RC-07", "C1") is None


def test_ut06_commercial_invoice_needs_buyer_legal_registration() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(legal_reg_type=None, legal_reg_id=None)]
    c["datasets"]["invoices"]["rows"] = [
        invoice_line(
            document_type="480",
            tax_category="O",
            tax_rate=None,
            invoice_tax_total="0.00",
            invoice_total="10000.00",
        )
    ]
    assert run_case(c).outcome("RC-08", "C1") == "fail"


def test_ut07_exchange_rate() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(currency="USD")]
    assert run_case(c).outcome("RC-12", "INV-1") == "fail"
    c["datasets"]["invoices"]["rows"] = [invoice_line(currency="USD", exchange_rate="3.6725001")]
    assert run_case(c).outcome("RC-12", "INV-1") == "fail"
    c["datasets"]["invoices"]["rows"] = [invoice_line(currency="USD", exchange_rate="3.6725")]
    assert run_case(c).outcome("RC-12", "INV-1") == "pass"


def test_ut08_units() -> None:
    c = clean_case(value_maps=[["unit", "pcs", "H87"], ["unit", "box-of-ten", "QQQ"]])
    c["datasets"]["items"]["rows"] = [
        item(item_id="I1", unit="pcs"),
        item(item_id="I2", unit="bundle"),
        item(item_id="I3", unit="box-of-ten"),
    ]
    r = run_case(c)
    assert r.outcome("RC-14", "I1") == "pass"
    assert r.outcome("RC-14", "I2") == "not_checked"
    assert (
        next(f for f in r.findings if f.record_key == "I2").not_checked_reason == "value_unmapped"
    )
    assert r.outcome("RC-14", "I3") == "fail"


def test_ut08_unapproved_value_mapping_is_not_used() -> None:
    # The engine only receives approved mappings; a suggestion never reaches it.
    c = clean_case()
    c["datasets"]["items"]["rows"] = [item(unit="pcs")]
    assert run_case(c).outcome("RC-14", "I1") == "not_checked"


def test_ut09_arithmetic() -> None:
    c = clean_case()
    assert run_case(c).outcome("RC-17", "INV-1") == "pass"
    c["datasets"]["invoices"]["rows"] = [invoice_line(invoice_total="10500.01")]
    assert run_case(c).outcome("RC-17", "INV-1") == "fail"
    c["datasets"]["invoices"]["rows"] = [invoice_line(invoice_total="10,500.00")]
    assert run_case(c).outcome("RC-17", "INV-1") == "pass"
    c["datasets"]["invoices"]["rows"] = [invoice_line(invoice_total="10500.001")]
    assert run_case(c).outcome("RC-17", "INV-1") == "fail"


cents = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("99999.99"), places=2)
qtys = st.decimals(min_value=Decimal("0.001"), max_value=Decimal("9999.999"), places=3)
rates = st.sampled_from(["5", "0", "5.00"])


@settings(max_examples=150, deadline=None)
@given(q=qtys, p=cents, rate=rates, q2=qtys, p2=cents)
def test_ut09_property_no_float_drift(
    q: Decimal, p: Decimal, rate: str, q2: Decimal, p2: Decimal
) -> None:
    n1, n2 = money(q * p), money(q2 * p2)
    net = n1 + n2
    tax = money(net * Decimal(rate) / 100)
    lines = [
        invoice_line(
            quantity=str(q),
            unit_price=str(p),
            line_net=str(n1),
            tax_rate=rate,
            invoice_net_total=str(net),
            invoice_tax_total=str(tax),
            invoice_total=str(net + tax),
        ),
        invoice_line(
            quantity=str(q2),
            unit_price=str(p2),
            line_net=str(n2),
            tax_rate=rate,
            invoice_net_total=str(net),
            invoice_tax_total=str(tax),
            invoice_total=str(net + tax),
        ),
    ]
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = lines
    assert run_case(c).outcome("RC-17", "INV-1") == "pass"
    for line in lines:
        line["invoice_total"] = str(net + tax + Decimal("0.01"))
    assert run_case(c).outcome("RC-17", "INV-1") == "fail"


def test_rc11_manual_review_does_not_stop_other_checks() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(document_type="261", invoice_total="1.00")]
    r = run_case(c)
    assert r.outcome("RC-11", "INV-1") == "manual_review"
    assert r.outcome("RC-17", "INV-1") == "fail"


def test_rc11_type_not_derivable_is_not_checked() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(document_type="Proforma")]
    assert run_case(c).outcome("RC-11", "INV-1") == "not_checked"


def test_rc09_duplicate_invoice_number() -> None:
    c = clean_case()
    c["datasets"]["invoices"]["rows"] = [invoice_line(), invoice_line(issue_date="2027-02-02")]
    assert run_case(c).outcome("RC-09", "INV-1") == "fail"


def test_ut12_identical_result_hash() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [
        customer(trn=None),
        customer(customer_id="C2", emirate="Dubayy"),
    ]
    assert run_case(c).result_hash == run_case(c).result_hash


def test_ut14_other_checks_still_run_on_an_excepted_record() -> None:
    # Exceptions are not an engine input, so an exception on RC-07 cannot suppress the
    # emirate check on the same record (RC-06; UT-14 text says RC-04, see docs change).
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(trn=None, emirate="DUB")]
    r = run_case(c)
    assert r.outcome("RC-07", "C1") == "fail"
    assert r.outcome("RC-06", "C1") == "fail"


def test_ut18_vat_group_grace_period() -> None:
    def outcome(day: str) -> str | None:
        c = clean_case()
        c["datasets"]["customers"]["rows"] = [customer(buyer_class="vat_group_member")]
        c["datasets"]["invoices"]["rows"] = [invoice_line(issue_date=day)]
        r = run_case(c)
        return r.outcome("RC-05", "INV-1", "invoices") or r.outcome("RC-17", "INV-1")

    assert outcome("2028-12-31") == "grace_period"
    assert outcome("2029-01-01") == "pass"
    assert outcome("2026-12-31") == "pass"


def test_missing_dataset_runs_no_rules_on_it() -> None:
    c = clean_case()
    c["datasets"]["invoices"] = None
    r = run_case(c)
    assert not [x for x in r.results if x.dataset == "invoices"]


def test_unmapped_column_is_not_checked() -> None:
    c = clean_case()
    c["datasets"]["customers"]["fields"] = {"emirate": None}  # column not mapped at all
    r = run_case(c)
    assert r.outcome("RC-06", "C1") == "not_checked"
    f = next(f for f in r.findings if f.rule_code == "RC-06")
    assert f.not_checked_reason == "column_unmapped"


def test_unknown_buyer_class_blocks_dependent_rules() -> None:
    c = clean_case()
    c["datasets"]["customers"]["rows"] = [customer(buyer_class="Trade customer", trn=None)]
    r = run_case(c)
    assert r.outcome("RC-05", "C1") == "not_checked"
    assert r.outcome("RC-07", "C1") == "not_checked"
