# AGENTS.md — PINT AE Readiness Desk

Canonical instructions for any agent or developer working in this repository. No application code exists yet. **Every command in this file is proposed** and will not run until an implementation is added.

## 1. Reading order

1. [Decision.md](Decision.md): the decision, the legal segments and dates, the economics, the stop rule.
2. [PRD.md](PRD.md): must-haves MH-01 to MH-15, rule checks RC-01 to RC-20, status vocabulary, metrics.
3. [TRD.md](TRD.md): architecture, API, jobs, security selections.
4. [App-flow.md](App-flow.md) and [design.md](design.md): screens S-01 to S-18 and their look.
5. [schema.md](schema.md): tables, permissions, retention, migrations.
6. [execution-plan.md](execution-plan.md): tasks and tests.
7. [verification-report-fixing.md](verification-report-fixing.md): traceability, risks R-01 to R-22, findings.

## 2. Sources of truth

| Subject | File | Never restate in |
|---|---|---|
| Labels, sources, segments, calendar, rule-pack versions, prices, economics, stop rule | Decision.md | Any other file |
| Requirements, rule checks, statuses, metrics | PRD.md | TRD, schema |
| Architecture decisions AD-nn, API, jobs | TRD.md | App-flow |
| Screens and routes | App-flow.md | design.md |
| Design decisions DD-nn, microcopy, accessibility map | design.md | App-flow |
| Tables, permissions, retention | schema.md | TRD |
| Tasks and tests | execution-plan.md | verification file |
| Risks, traceability, findings | verification-report-fixing.md | Any other file |

Label every number as [C], [S: SRC-nn], [A] or [P] (Decision.md section 0). An assumption is never written as a finding. A legal date is never written without its source.

## 3. Product boundaries

- Not an Accredited Service Provider. No invoice transmission, no e-invoice XML, no claim that a result is an ASP validation.
- No connection to the FTA, EmaraTax, any ASP, QuickBooks or Odoo in the MVP. Non-goals and the evidence that admits each: PRD.md section 2.
- Upload-only, sales-side, English-only, firm users only.
- The product never edits client data and never asks a user to invent a value; "unknown" is a valid answer everywhere.

## 4. Architecture conventions (proposed)

- Layout: `apps/web`, `apps/api`, `apps/worker`, `packages/core`, `packages/rules`, `packages/rulepacks`, `packages/ingest`.
- Apps import packages through public interfaces only; `api` and `worker` never import each other; `packages/core` imports no web framework.
- Reuse before writing: tenancy session, configuration, logging, date helper, storage-key builder, rule engine, status function and calendar lookup each exist once. Search for them first.
- Dates are `date` values in Asia/Dubai. Money and quantities use decimal arithmetic. No model is used for segment, deadline, arithmetic, status or access.
- Rule packs and calendars are versioned data files, immutable after publication. A correction is a new version.
- Every result stores the versions it used; approval re-checks them. Staleness and supersession are derived on read, never stored and never left to a job.
- An outcome of "not checked" on a blocker rule is an open blocker.
- Vendor staff are not firm users; they reach tenant rows only through an Owner's grant.
- Long work is a job: return 202, poll, idempotency key on every mutating request.

## 5. Tenant safety

- Every tenant table has `firm_id` and a row-level security policy. Open database sessions only through the tenancy session, in the API and in the worker.
- Foreign identifiers return 404 and write an audit event.
- Object keys start with `firms/{firm_id}/`. Files are streamed through the API.
- No cache without a design change that updates R-05.
- Logs carry identifiers and counts, never cell values, names or TRNs.

## 6. Migrations

- One linear history; a second head fails CI.
- Models and migrations must produce the same schema (`scripts/check_schema_parity`, proposed).
- Add columns nullable, backfill with a resumable job, then constrain. Build indexes on large tables concurrently.
- Never run a backfill inside a schema migration.

## 7. Tests

- A change to a rule, the calendar, the segment function or the status function needs a unit test with a synthetic fixture and an expected outcome first.
- A new endpoint is added to the tenant and permission suite (IT-01, IT-02) in the same change.
- Fixtures are synthetic (FX-A to FX-E). Never commit customer data, credentials, tokens or real TRNs.
- Proposed commands: `make dev`, `make test`, `make e2e`, `scripts/check_schema_parity`, `scripts/load_rulepack <file>`.

## 8. When something changes, update these

| Change | Update |
|---|---|
| A requirement | PRD.md row; traceability row; affected task and test in execution-plan.md |
| A screen, action or route | App-flow.md inventory and screen entry; the endpoint table in TRD.md section 5.1 (every action needs a row); design.md if layout or microcopy changes; traceability row; NAV-01 route table |
| A permission or role | schema.md permission matrix; PRD.md roles; App-flow.md role column; IT-02 |
| A table, field, index or retention period | schema.md; migration plan; R-08 parity; traceability row |
| A legal date, segment, provision or source version | Decision.md section 3 and section 13; calendar and provisions data file as a new CAL or PRV entry; UT-10, UT-16, UT-18; S-14 content |
| A rule check | PRD.md section 6; rule-pack file as a new version; unit test |
| A price, cost, rate or other operating assumption | Decision.md sections 6 to 9 and 12 together, then re-run the arithmetic; never one number alone |
| An architecture decision | TRD.md section 9; affected risks in the verification file |
| A risk's prevention or test | verification-report-fixing.md section 5 only |

## 9. Git hygiene

- Default branch `main`, protected. Branch names `type/T-x.y.z-slug`.
- One task per pull request; the description cites the MH, R or task ID.
- Do not delete an unmerged branch that is not yours. Do not rewrite shared history.
- Planning repository rule: exactly ten root files until implementation begins.

## 10. Reporting completion accurately

- Say what was run and what was not. A planned control is not evidence. A test that was not executed is `Not run`.
- Never report a client, a rule or the product as "compliant".
- If a source could not be opened, write "unverified, no source consulted".
- Record fixes in the findings register; only the reviewer records a retest result.
