# PRD — PINT AE Readiness Desk

Labels and sources: [Decision.md section 0](Decision.md#0-labels) and [section 13](Decision.md#13-sources-and-assumptions). Segments (SEG-), calendar rows (CAL-) and rule packs (RP-) are defined once in [Decision.md section 3](Decision.md#3-rules-by-effective-date-and-client-segment). Everything here is a proposal **[P]** unless labelled.

## 1. Overview

A UAE bookkeeping or tax firm uploads each client's customer list, item list and recent sales invoices. The product checks them with deterministic rules against a versioned rule pack, classifies each client into a legal segment with its own deadlines, and shows one cross-client view of who is data-ready, who has appointed an ASP and how many days remain. It is **not an ASP**: it transmits nothing, produces no e-invoice XML and its pass is not an ASP's acceptance.

**Why now.** SEG-S clients must appoint an ASP by 31 March 2027 and implement by 1 July 2027 [S: SRC-05]. The trigger weakens after that date ([Decision.md 5.3](Decision.md#53-the-recurring-job-after-onboarding-p)).

**Decisive question.** Whether a firm pays after accounting for its ASP's free validation. The product must therefore record, per client, what the ASP already covered (MH-10), not only its own findings.

## 2. Goals and non-goals

Goals: G1 a gap report per client entity within 2 business days of a complete upload; G2 no client shown as ready when it is not; G3 a cross-client deadline view by segment; G4 evidence for the month-3 decision: the ASP-overlap rate and the monthly-cycle usage.

Non-goals for the MVP, with the evidence that would admit each:

| Non-goal | Admitted when |
|---|---|
| Transmitting invoices, generating PINT AE XML, running the official Schematron | Never without accreditation; XML preview only if 2 pilot firms ask and an ASP partner agrees |
| QuickBooks Online and Odoo connectors (brief: "connect later" [C]) | 3 pilot firms name the same connector as the reason uploads fail |
| ASP-specific import formats | A pilot firm supplies the ASP's template |
| Client-facing logins | A pilot firm's clients ask to fix data themselves |
| Arabic interface | A signed pilot requires it |
| Purchase-side (received invoice) readiness | After sales-side pilots convert |
| Self-billing documents (type codes 389, 261) | A pilot client self-bills; until then such rows get the `manual_review` outcome and block Data-ready until a Reviewer resolves them (section 5) |

## 3. Problem, buyer, users

Problem and workaround: [Decision.md section 2](Decision.md#2-market-people-current-practice). Buyer: the managing partner.

| Role | Person | Can |
|---|---|---|
| Owner | Managing partner | Everything a Reviewer can; users, plan, data deletion, vendor-support grants |
| Reviewer | Tax agent or head of VAT | Approve segments, mappings and reports; accept exceptions; record ASP status |
| Preparer | Accounting manager, bookkeeper | Create client entities, upload, map, propose fixes and segments; cannot approve |
| Vendor support | Founder | No access by default; time-boxed, read-only, Owner-granted, audited |

**Current workflow.** Spreadsheet of clients and a yes/no ASP column; exports opened one by one; TRNs and units checked by eye; a vendor checklist emailed to the client.

**Proposed workflow.** Add client entity → classify segment (Reviewer approves) → upload three datasets → confirm column mapping → check run → fix list → client or Preparer fixes at source → re-upload → Reviewer approves → report and handoff pack → record ASP appointment → monthly cycle.

## 4. Must-haves

Priority P0 = needed for the paid pilot on the application (MH-15 is P0 because the pilot promises a handoff pack); P1 = needed by pilot day 31 to test the recurring job.

| ID | P | User story | Observable acceptance criteria | Owner role |
|---|---|---|---|---|
| MH-01 | P0 | As an Owner I want a firm workspace with roles so that only my staff see my clients' data | A user of firm A receives 404 for every firm B identifier in pages, API, exports and files; role limits of section 3 hold server-side; password plus TOTP sign-in | Owner |
| MH-02 | P0 | As a Reviewer I want each client classified into a legal segment so that its deadlines are right | Entity type and Revenue band are recorded with accounting-period end and evidence type; Revenue may be `unknown` (SEG-U) without blocking any other step; a Preparer's proposal takes effect only on Reviewer approval; every change creates a new version and marks prior reports superseded | Reviewer |
| MH-03 | P0 | As a Reviewer I want deadlines from a versioned calendar so that a changed decision changes every affected client | Each displayed date shows segment, calendar version and source and is always read from the current published calendar, never from an old result; SEG-U follows the one rule in Decision §3: both outcomes shown, earliest possible date used for sorting and days-left; SEG-N shows "before first invoice"; days remaining are computed in Asia/Dubai; a new calendar version changes the dates at once and supersedes approved reports that printed the old ones | Reviewer |
| MH-04 | P0 | As a Preparer I want to upload customers, items and invoices as Excel or CSV | .xlsx and .csv up to 20 MB and 200,000 rows; type, size and content checked; re-uploading the same bytes for the same entity and dataset creates no second dataset; each file ends in exactly one of accepted, rejected with reason | Preparer |
| MH-05 | P0 | As a Preparer I want suggested column mappings that I confirm and a Reviewer approves so that messy exports work and a wrong column is caught | Every target field is mapped or marked "not in this file"; a field that is not mapped makes its rules "not checked", which blocks Data-ready (MH-08) and is shown before confirming; nothing is checked until a Preparer confirms; a run may start on a confirmed mapping, but no report can be approved until a Reviewer has approved every column mapping and value table it used, seeing five sample values per field; a confirmed mapping is reused for the same entity and header fingerprint and needs approval once per version | Preparer confirms; Reviewer approves |
| MH-06 | P0 | As a Reviewer I want every record checked by deterministic rules from a named rule pack | Every in-scope record receives every applicable check in section 6, whatever else failed or was excepted on that record; the result stores rule pack version and mapping version; the same input and versions give the same output | Reviewer |
| MH-07 | P0 | As a Preparer I want a fix list with source evidence so that the client can correct the source | Each finding shows file, sheet, row, column, the value found, the rule, its source reference and what a valid value looks like; export to .xlsx; findings group by cause | Preparer |
| MH-08 | P0 | As an Owner I want a status per client that never overstates readiness | Statuses of section 5; "Data-ready" requires all of: zero failed blocker checks; zero "not checked" results on any blocker rule; zero unresolved manual-review records; zero accepted exceptions; confirmed segment; all three datasets, each with at least one data row, and the seller profile present; mappings approved; current rule pack; data no older than 45 days; Reviewer approval. An accepted exception gives "Exceptions open"; an unchecked mandatory field gives "Checks incomplete"; neither is ever "Data-ready" | Reviewer |
| MH-09 | P0 | As an Owner I want one dashboard across clients sorted by risk | One row per entity: segment, appoint-by and implement-by dates, days remaining, data status, ASP status, open blockers, unchecked rules; default sort: entities past their governing appoint-by date without an appointment first (SEG-U rows by their earliest possible date), then by days remaining; filter and sort survive reload and sharing by URL; totals equal the sum of rows | Owner |
| MH-10 | P0 | As a Reviewer I want to record ASP appointment and what the ASP's own checks found | Per entity: ASP name from the MoF list or free text, appointment date, EmaraTax onboarding done, evidence note; optional "ASP also flagged this" mark on findings; entities past appoint-by without an appointment are listed first | Reviewer |
| MH-11 | P0 | As a Reviewer I want to approve a white-label readiness report | Draft is watermarked; the approval view shows status, exceptions, unchecked rules, segment, mappings with samples, versions; approval freezes content and versions; every page states "not an Accredited Service Provider; not an ASP validation result", the check date, a reference code and "valid only while your accountant's record for this code shows Current"; a later change marks the report superseded and lists it under "Reports to re-issue" | Reviewer |
| MH-12 | P0 | As a Reviewer I want rule and calendar updates applied visibly | Publishing a new rule pack makes affected entities "Stale" on the next read; publishing a new calendar version changes dates at once, makes results that applied the old calendar Stale and marks reports that printed the old dates Superseded; re-run is one action; old results stay readable with their version; no result is silently re-scored | Vendor publishes; Reviewer re-runs |
| MH-13 | P1 | As an Owner I want a monthly cycle so that readiness is kept, not reached once | Per month: delta uploads checked, stale entities re-run, rejections logged with cause, new entities started; a monthly summary lists changes since the last cycle; each cycle closes with a named Reviewer | Reviewer |
| MH-14 | P0 | As an Owner I want audit, export and deletion | Every approval, exception, segment change, upload, export and support grant is in an append-only log; all firm data exports as files; deleting an entity removes its files and rows within the stated period and survives a restore | Owner |
| MH-15 | P0 | As a Preparer I want a handoff pack of cleaned master data | Generic .xlsx with customers and items in rule-pack field order; refused, with the reason, while either dataset has a failed or unchecked blocker; states the pack version and that ASP formats differ | Preparer |

## 5. Status vocabulary

Every check on a record has one outcome: `pass`, `fail`, `not_checked` (the rule could not run: its field was marked "not in this file", its column is unmapped, or a value has no approved mapping), `manual_review` (the record is of a kind the product does not assess: self-billed documents, type codes 389 and 261), `grace_period` (PRV-2: an Excluded Transaction between members of the same Tax Group, invoices dated 1 January 2027 to 31 December 2028, MD 197 of 2026 [Decision.md SRC-25]; the finding text names the provision, its end date and its sources) or `out_of_scope`. **A `not_checked` outcome on a blocker rule and an unresolved `manual_review` record each count as an open blocker.** Neither is ever a pass or silent. A Reviewer resolves a manual-review record in one of two ways: confirm it is self-billed, after which it leaves the denominator and every report lists it under "Not assessed by this product: self-billed documents" with the count; or correct its document type, after which it is checked normally. A Preparer cannot resolve it.

Data status, one per entity, first matching row wins:

| Order | Status | Condition |
|---|---|---|
| 1 | Not started | No upload |
| 2 | Segment not confirmed | No approved segment, or SEG-U |
| 3 | Data incomplete | A dataset or the seller profile is missing |
| 4 | Gaps open | At least one failed blocker check |
| 5 | Checks incomplete | No failed blocker, at least one `not_checked` blocker rule or unresolved `manual_review` record |
| 6 | Exceptions open | Neither of the above, at least one accepted exception |
| 7 | Review pending | None of the above; awaiting mapping approval or Reviewer approval |
| 8 | Data-ready | Reviewer approved |

`Stale` replaces statuses 6 to 8 when the result's rule pack, segment version, mapping version or seller-profile version is not the current one, or its newest data is older than 45 days **[A]**. A new calendar version also makes a result Stale, because a run applies the calendar's provisions (for example the PRV-2 grace period decides which invoices are checked): every run pins the calendar version it used, the version is part of the run's input hash, so a re-run after a new calendar produces a new run (B1 review B1-001, 2026-11-11). A new calendar also changes every displayed date at once and makes Superseded every approved report that printed the old dates. A newer upload for any dataset makes the result Stale as soon as the upload is received, before it is parsed. A required dataset that is mapped but has no data rows below its header gives `Checks incomplete` (reason: dataset has no rows), never Data-ready. The 45-day age is measured from the date the newest file was uploaded, not from the dates inside it **[P]**. Staleness is computed every time a status is read, from the stored versions and today's date in Asia/Dubai; it does not depend on any background job. Deadlines are not part of a result: they always come from the current calendar. ASP status is separate: `Not appointed`, `Appointed`, `Onboarded`, `Live`. The data status never says or implies whether an entity will meet, or has met, its appointment or implementation date: a data check cannot show that. Only the ASP status recorded by the Reviewer from the client's evidence, read against the calendar date, drives "past appoint-by without ASP" (C1, 2026-11-11; UT-21). The word "compliant" is never used.

**Readiness score** [C: "readiness score"]: records with `pass` on every applicable blocker rule ÷ in-scope records, per dataset. `fail` and `not_checked` records are in the denominator and not in the numerator; `out_of_scope` records (consumer buyers) are in neither. It is shown beside the status and never replaces it.

## 6. Rule checks in pack RP-1

Severity: B = blocker, W = warning for Reviewer judgment. "MF" = mandatory-field number in [S: SRC-03]; rule IDs from [S: SRC-12]; BIS = [S: SRC-13]; GL = [S: SRC-02].

| ID | Check on source data | Applies to | Sev | Reference |
|---|---|---|---|---|
| RC-01 | Seller VAT TRN is 15 digits, starts with 1, ends with 03 | VAT-registered seller | B | IBR-132-AE; MF 15 |
| RC-02 | Seller TIN is 10 digits of form 1XXXXXXXXX; one of TRN or TIN exists | Seller not VAT-registered | B | IBR-148-AE, IBR-177-AE; GL §18.1.1 |
| RC-03 | Seller legal registration identifier and type (TL, EID, PAS, CD); authority name when TL; issuing country when PAS | Seller profile | B | IBR-150-AE, IBR-173-AE, IBR-172-AE, IBR-012-AE; MF 13–14 |
| RC-04 | Seller address line, city, country as an ISO 3166 alpha-2 code (UAE spellings such as "UAE" or "United Arab Emirates" normalised to AE; other free text needs an approved value mapping); emirate is one of AUH, DXB, SHJ, UAQ, FUJ, AJM, RAK whenever the country is AE | Seller profile | B | IBR-128-AE; MF 17–20 (SRC-03, 28 Oct 2026: "For UAE it should be AE"; changed in B1 review B1-003) |
| RC-05 | Buyer class recorded: UAE business, member of the seller's VAT group, government, foreign, consumer | All customers | B | GL §6.2, §6.3.2; SRC-05 Art. 5(2) |
| RC-06 | Buyer name, address line, city, country code as in RC-04; emirate code whenever the country is AE in any spelling | Business and government buyers | B | MF 21, 26–29 (SRC-03, 28 Oct 2026; B1-003); IBR-128-AE |
| RC-07 | UAE business buyer has a VAT TRN in RC-01 format or a TIN; a TIN alone is accepted here and recorded by RC-22 | Tax invoices, non-export | B | IBR-135-AE; MF 24 |
| RC-08 | Buyer legal registration identifier and type; authority name when TL; issuing country when PAS. A commercial invoice whose customer cannot be matched (link not in the file, empty, unknown or ambiguous) gives `not_checked` | Commercial invoices (codes 480, 81); UAE buyers whose electronic address is not TIN-based (1XXXXXXXXX or 9XXXXXXXXX); and, when the endpoint is absent or empty, every UAE business or government buyer without a TIN-shaped TRN or TIN (checked, never skipped; B1-013) | B | IBR-136-AE, IBR-149-AE (PINT AE rule page, docs.peppol.eu, read by the B1 reviewer on 2026-11-11: IBT-047 required when the endpoint scheme is 0235 and the address is not TIN-based), IBR-101-AE, IBR-010-AE; SRC-02 §18.2.1 (26 Oct 2026: IBT-047 mandatory for 480 and 81; B1-007) |
| RC-09 | Invoice number present and unique within the seller | Invoices | B | MF 1 |
| RC-10 | Issue date valid; payment due date present | Invoices | B | MF 2, 6 |
| RC-11 | Document type derivable: 380, 381, 480 or 81. A record typed 389 or 261 gets outcome `manual_review` and blocks Data-ready until a Reviewer resolves it (section 5); a record whose type cannot be derived is `not_checked` | Invoices, credit notes | B | BIS §1.5.1 |
| RC-12 | Currency is an ISO 4217 code; when not AED an exchange rate with at most 6 decimals exists | Invoices | B | MF 4; IBR-159-AE, IBR-002-AE |
| RC-13 | Payment means present or mappable | Invoices | B | MF 9 |
| RC-14 | Line quantity present; unit maps to a UNECE Recommendation 20 or 21 code | Lines, items | B | MF 40–41; BIS §2.8 |
| RC-15 | Item name and description; net price, gross price, base quantity | Lines, items | B | MF 43–45, 50–51 |
| RC-16 | Tax category is one of the aligned codes and a rate exists unless exempt or out of scope | Lines, items | B | IBR-139-AE; MF 46–47; GL §10.5 |
| RC-17 | Arithmetic: line net, document totals, tax per category and payable agree to 0.01 in decimal arithmetic; document totals have at most 2 decimals | Invoices | B | BIS §4.1.2, §4.2; GL §12.2(5) |
| RC-18 | Code 480 used only where every line is out of scope, not exempt or zero-rated | Invoices | W | GL §18.3.1 |
| RC-19 | Invoice transaction type code present as 8 binary flags (free zone, deemed supply, margin, summary, continuous, agent, e-commerce, export). Deriving each flag from the entity questionnaire, and the beneficiary for a free-zone buyer, stay a Reviewer judgement (W, not yet a rule) | Invoices | B | MF 5 (SRC-03, 28 Oct 2026: mandatory for tax and commercial invoices; changed from W in B1 review B1-006); IBR-154-AE; GL §10.4 |
| RC-20 | Credit note carries a reason and a preceding invoice reference, except volume discount | Credit notes | B | BIS §1.5.1 |
| RC-21 | One customer record per customer ID (rows with the same ID and different details fail); each invoice's customer ID matches exactly one customer (no match fails; a conflicting match is `not_checked`, and the invoice stays in scope) | Customers, invoices | B | MF 21–29 (SRC-03) [P]; added in B1 review B1-004 |
| RC-22 | UAE business buyer identified by a TIN only: recorded for the Reviewer, because a VAT-registered buyer must give its TRN | Business buyers | W | MF 24 (SRC-03, 28 Oct 2026: VAT-registered UAE buyers "should provide the TRN") |

Not in RP-1 (gap stated after the B1 review): MF 22–23 (buyer electronic address), 34 (amount due), 39 (line identifier), 48–49 (VAT line amount and line amount in AED) [S: SRC-03]. Several are produced by the ASP from the invoice; none is checked at source-data level here, so a pass does not cover them.

**Where seller data comes from.** RC-01 to RC-04 run on the seller profile, which the Preparer types on S-05 from the client's trade licence and its EmaraTax profile (MoF tells taxpayers to verify those details in EmaraTax before onboarding [S: SRC-02 §15.3]): legal name, registration type, licence number and authority, address line, city, emirate, country, VAT status, TRN or TIN. Any item may be "unknown"; an unknown item makes its rule `not_checked`.

Rules of application: a consumer buyer is out of scope and leaves the denominator, it does not fail (SRC-05 Art. 5(2)). A user who cannot supply a value records a classification or "unknown" with a reason; the product never asks for an invented number. Invoices to a member of the seller's VAT group ("Tax Group" in MD 197 of 2026, which makes them Excluded Transactions for 24 months from 1 January 2027) dated 1 January 2027 to 31 December 2028 are marked "grace period" (PRV-2), reported separately with the provision's end date and sources, and left out of the denominator; the same invoice dated 1 January 2029 or later is checked normally. Rules carry optional validity dates so that a provision such as PRV-3 can switch a rule on from a date. The margin-scheme tax category code was not confirmed at source and is treated as W until read.

## 7. Highest-cost user mistake and highest-consequence failure

**Highest-consequence failure (ranked first, named the same in every document): False Ready** — a client entity is shown or reported as data-ready, or with a later deadline than the law gives it, when it is not. The firm tells the client it is safe; the client misses the appointment date or has invoices rejected after go-live.

**Highest-cost user mistake:** approving a Revenue band below AED 50M for a client at or above it, or confirming a mapping that puts the wrong column in a checked field (for example a corporate tax number in the VAT TRN column). Reviewed by: the Reviewer, who must approve the segment on S-06 and every column mapping and value table on S-08, each with evidence and five sample values per field, and who sees the approved mappings again on S-12 before approving a report. A Preparer cannot approve either. Corrected by: a new segment version or mapping version; both force a re-run, mark earlier reports superseded and list the entities whose status changed.

## 8. Dependencies and constraints

Dependencies: client authority to share data; MoF and OpenPeppol publications (no change feed; checked weekly by hand from Phase 0, execution-plan T-0.1.7); a UAE-region store from the first file (T-0.1.5) and host; written answers to legal questions LQ-1 to LQ-5 (Decision §12; C2, 2026-11-11: answered by compliance/self-check.md, owner sign-off recorded, no lawyer). Constraints: not an ASP and must say so [C] (wording: compliance/self-check.md section 9.4); data kept in the UAE region [C] (staging and production refuse a non-UAE storage region, C2); one founder, 1–3 developers in Vancouver, 11–12 hours from Dubai [C]; personal-data law read in Arabic in C2 (compliance/self-check.md section 4; Executive Regulations not issued); English only.

## 9. Success metrics

| ID | Kind | Metric | Method and source | Denominator | Window | Baseline | Target [P] |
|---|---|---|---|---|---|---|---|
| M-01 | Commercial | Paid pilots | Bank receipt and signed agreement | — | To day 77 after the first send (28 February 2027 for a 14 December 2026 start) | 0 | ≥ 2 (Decision SR-1) |
| **M-02 (primary: the decisive metric)** | Commercial | Month-3 conversion | Month-3 invoice paid by day 60 | Pilots reaching day 60 | Per pilot | Unknown | ≥ 2 of first 3 (SR-3) |
| M-03 | Commercial | ASP overlap | Blocker findings marked "ASP also flagged" (MH-10) | Blocker findings on entities that have begun ASP onboarding | Pilot days 1–60 | Unknown | Report only; above 80% argues against the product |
| M-04 | Workflow | Turnaround | Hand delivery: UAE business days (Decision §5.2) from the later of intake slot and `intake_complete_at` to `delivered_at`, from the delivery log. Application: minutes from mapping confirmed to run finished | Entities with complete files by day 30 | Pilot | None | ≥ 80% within 2 business days (refund criterion); on the application ≥ 80% within 1 hour |
| M-05 | Workflow | Gap closure | Blockers open at first run and closed at the latest run, matched by rule and record key | Blockers at first run on entities with ≥ 2 runs | Pilot | 0 | ≥ 60% |
| M-06 | Workflow | Reviewer minutes per entity | Stopwatch on 2 entities in week 1 without the product, then session time between opening and approving | Entities approved | Pilot | Brief's 3 h per client [C-model], replaced by the measured figure | ≤ 60 minutes |
| M-07 | Workflow | Monthly-cycle use | Cycles closed by a Reviewer | Accounts past day 60 | Monthly | 0 | ≥ 1 cycle per account-month |
| M-08 | Failure | False Ready | Entities approved Data-ready that an ASP later rejects for a field covered by RP-1, reported by the firm, plus any found by re-running a newer pack | Entities approved Data-ready | Rolling | 0 | 0; each case is an incident |
| M-09 | Failure | Wrong segment or deadline | Segment versions corrected after approval | Approved segment versions | Rolling | 0 | 0 |
| M-10 | Failure | Uploads not ending in a terminal state within 15 minutes | Job table | Uploads | Weekly | — | 0 |

M-02 decides the question this repository exists to answer; the other nine explain the result.

**Expanding the MVP** is justified only by M-02 met and M-03 below 80%, then by the per-row evidence in section 2.
