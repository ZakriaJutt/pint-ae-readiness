# AGENTS.md — PINT AE Readiness Desk

Canonical instructions for any agent or developer working in this repository. Build milestone B1 (foundation and deterministic core, started 2026-11-11 on the owner's authorisation before the Phase 0 gate) exists on branch `feat/b1-foundation`: Python packages, migrations, a minimal API and worker, and tests. Milestone B2 (branch `feat/b2-local-auth`) adds real sign-in (password plus TOTP, invitations, sessions with anti-forgery tokens, throttle, password reset, recovery codes), e-mail through SMTP to the local Mailpit inbox, and object storage through the S3 API to local MinIO. There is no web frontend, no vendor sign-in and no real provider account. Commands marked **exists** in section 7 run; all others remain proposed.

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

### 4.1 Utilities index (B1; reuse these, do not copy them)

| Concern | The one implementation |
|---|---|
| Settings (read once, validated; `PUBLIC_BASE_URL` rule) | `packages/core/pintae_core/config.py` |
| Structured logging, correlation identifier, field allow-list | `packages/core/pintae_core/logging.py` |
| Asia/Dubai date helper | `packages/rules/pintae_rules/dates.py` |
| Tenancy session (the only way to open a database session) | `packages/core/pintae_core/tenancy.py` |
| ORM models, tenant and global table lists, expected migration head | `packages/core/pintae_core/models.py` |
| Storage-key builder and object-store interface (S3 API for MinIO and S3; directory fake for tests) | `packages/core/pintae_core/storage.py` |
| Jobs: enqueue, claim, lease sweep, compare-and-set completion, heartbeat | `packages/core/pintae_core/jobs.py` |
| Audit events | `packages/core/pintae_core/audit.py` |
| Idempotency keys | `packages/core/pintae_core/idempotency.py` |
| Runs, snapshots, status read, report pins and currency | `packages/core/pintae_core/readiness.py` |
| Verified reference-data loaders (recompute the content hash; refuse a mismatch): `load_pack`, `current_pack`, `current_calendar`, `calendar_by_code` | `packages/core/pintae_core/readiness.py` |
| Sign-in primitives: password hashing and policy, TOTP, TOTP-secret sealing, tokens, anti-forgery tokens, recovery codes | `packages/core/pintae_core/auth.py` (breached-password set: `breached.py`) |
| Sign-in flows: invitations, password and TOTP steps, recovery codes, password reset, sign-out, users | `packages/core/pintae_core/identity.py` |
| Session cookie, anti-forgery check, client address (API) | `apps/api/pintae_api/deps.py` |
| Outgoing e-mail (SMTP; Mailpit locally) | `packages/core/pintae_core/mail.py` |
| Generated files and CSV formula escaping | `packages/core/pintae_core/exports.py` |
| Session before a firm is known (sign-in only) | `packages/core/pintae_core/tenancy.py` `global_session` |
| Rule-pack and calendar publication (two steps) and withdrawal (`withdraw`, status only, terminal) | `packages/core/pintae_core/publication.py` |
| Rule engine and evaluators | `packages/rules/pintae_rules/engine.py` |
| Rule-pack loading, hashing, selection by effective date | `packages/rules/pintae_rules/packs.py` |
| Segment function | `packages/rules/pintae_rules/segment.py` |
| Calendar lookup and deadline view | `packages/rules/pintae_rules/calendar.py` |
| Status function and staleness derivation | `packages/rules/pintae_rules/status.py` |
| Dashboard risk sort | `packages/rules/pintae_rules/dashboard.py` |
| Rule-pack golden-fixture runner | `packages/rules/pintae_rules/fixtures.py` |
| File checks and parsers (.xlsx, .csv) | `packages/ingest/pintae_ingest/parsers.py` |
| Column mapper, synonym dictionary, header fingerprint | `packages/ingest/pintae_ingest/mapper.py` |
| RP-1, CAL-1, CAL-2 data and RP-1 fixtures | `packages/rulepacks/pintae_rulepacks/` |

## 5. Tenant safety

- Every tenant table has `firm_id` and a row-level security policy. Open database sessions only through the tenancy session, in the API and in the worker.
- Foreign identifiers return 404 and write an audit event.
- Object keys start with `firms/{firm_id}/`. Files are streamed through the API.
- No cache without a design change that updates R-05.
- Logs carry identifiers and counts, never cell values, names or TRNs.

## 6. Migrations

- One linear history; a second head fails CI.
- Models and migrations must produce the same schema (`scripts/check_schema_parity.py`, exists; `make parity`).
- Add columns nullable, backfill with a resumable job, then constrain. Build indexes on large tables concurrently.
- Never run a backfill inside a schema migration.

## 7. Tests

- A change to a rule, the calendar, the segment function or the status function needs a unit test with a synthetic fixture and an expected outcome first.
- A new endpoint is added to the tenant and permission suite (IT-01, IT-02) in the same change.
- Fixtures are synthetic (FX-A to FX-E). Never commit customer data, credentials, tokens or real TRNs.
- Commands. **Exists** (B1, run from the repository root): `make venv`, `make dev` (database, migrations, reference data, worker, API on port 8105, waits for `/readyz`, which also verifies the reference data in force against its content hash), `make dev-check` (OPS-04), `make test` (rebuilds the `pintae_test` schema, then unit and integration tests), `make lint` (ruff), `make typecheck` (mypy strict), `make arch` (ARCH-01, `scripts/check_imports.py`), `make parity` (`scripts/check_schema_parity.py`), `python scripts/load_rulepack.py <file> --publisher-email <e> [--confirm-hash <hex>]`, `python scripts/create_firm.py --name <n> --owner-email <e>` (B2: vendor onboarding, e-mails the first Owner's invitation). **Still proposed**: `make e2e`, `scripts/run_checks_cli`, `scripts/seed_synthetic`, `scripts/restore_drill`, `scripts/sweep_expired`.
- Local environment: Python 3.12 virtual environment at `backend/.venv`; PostgreSQL `pintae_dev` and `pintae_test` used through the role `pintae_app` (NOSUPERUSER NOBYPASSRLS); the owner role only for migrations and publication. Redis database index 4 is assigned but unused (TRD AD-02). B2: copy `backend/.env.example` to `backend/.env` (gitignored) and fill in `PINTAE_SECRET_KEY`, `PINTAE_TOTP_KEY` and the local MinIO credentials; Mailpit at SMTP `127.0.0.1:1025` (inbox http://127.0.0.1:8025) and MinIO at `http://127.0.0.1:9000`, bucket `pintae-dev`, must be running for the B2 integration tests (they skip with a reason otherwise). Integration tests sign in with seeded `full` sessions sent as the real cookie with its anti-forgery token (test-only); `test_b2_sign_in.py` covers the real sign-in. Docker is not used locally; the Compose setup in TRD section 7 stays proposed.

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
