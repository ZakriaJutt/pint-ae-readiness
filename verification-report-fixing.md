# Verification, findings and fixes — PINT AE Readiness Desk

Labels: [Decision.md section 0](Decision.md#0-labels). This file is the single home of the production risk register (R-01 to R-22) and of the findings register.

## 1. Status summary

| Item | State on 2026-11-10 |
|---|---|
| Application | B1 foundation and deterministic core built on 2026-11-11 (branch `feat/b1-foundation`, owner authorisation before the Phase 0 gate); results in section 9. Every check not listed there is `Not run` |
| Customer evidence | None. No interview, no message sent, no pilot |
| Documents | Ten files written by Author A; independent review round 1 returned 19 findings; round 2 verdicts: 14 closed, 4 closed with a part open, 1 open by design, plus 2 new (F-020, F-021); the author fixed both and the F-001 residue on 2026-11-10; the reviewer's final retest on 2026-11-10 closed F-021 and the F-001 residue and closed F-020 with one leftover diagram date, which the lead then corrected (not re-reviewed) |
| Highest-consequence failure | **False Ready** — a client entity is shown or reported as data-ready, or with a later deadline than the law gives it, when it is not ([PRD.md section 7](PRD.md#7-highest-cost-user-mistake-and-highest-consequence-failure)) |
| Decisive question | Unanswered. The recurring job is defined as a proposal and has no evidence |

## 2. Checks performed on the documents (author)

| Check | Method | Result |
|---|---|---|
| Legal dates and segments | Read Ministerial Decisions 244 of 2025 and 66 of 2026 and the MoF Guidelines V2.0 in full text | Done; one conflict between instruments recorded (Decision §3) |
| Mandatory field counts and rule references | Read MoF Mandatory Fields V1.1 and the PINT AE rule and release pages | Done; rule severities not shown at source |
| What ASPs include | MoF Guidelines roles table and appendices; Wafeq and Zoho pages | Done; vendor text only |
| Economics | Recomputed by script from the stated inputs | Done; brief's 86%, 3.23, 8 and 43 reproduce |
| Stop-rule probability | Binomial computed by script | Done |
| Internal links, IDs, traceability, risk rows | Script, section 6.1 | Done |
| Security and accessibility references | ASVS 5.0.0 chapter text and WCAG 2.2 text read before citing | Done; two requirements marked not met |
| Fresh-reader, source-fidelity, commercial recalculation, walkthrough | Reviewer's tasks | Not done by the author |

## 3. Application checks planned for future implementation

All `Not run` except the B1 results recorded in [section 9](#9-b1-build-record-2026-11-11), which take precedence for the IDs they name. Definitions: [execution-plan.md section 8](execution-plan.md#8-tests).

| Group | IDs | Status |
|---|---|---|
| Unit | UT-01 to UT-19 | Not run |
| Integration | IT-01 to IT-21 | Not run |
| End-to-end | E2E-01 to E2E-08 | Not run |
| Load | LOAD-01 to LOAD-03 | Not run |
| Operations | OPS-01 to OPS-06 | Not run |
| Accessibility | A11Y-01 to A11Y-07 | Not run |
| Architecture, navigation, governance | ARCH-01, NAV-01, GOV-01, GOV-02 | Not run |

## 4. Traceability matrix

| Must-have | Screen or API | Design or architecture decision | Schema or permission | Task | Planned test |
|---|---|---|---|---|---|
| MH-01 Workspace, roles, isolation, recovery | S-01, S-02, S-03, S-15, S-17, S-18; `/auth/*`, `/invites`, `/users`, `/firm`, `/vendor/*` | AD-01, AD-05, AD-12 | `firms`, `users`, `sessions`, `invites`, `recovery_codes`, `password_resets`, `owner_resets`, `vendor_users`, `support_grants`; row-level security; role matrix | T-2.2.2, T-2.2.3, T-5.1.1 | IT-01, IT-02, IT-16, IT-18, IT-21, E2E-07 |
| MH-02 Segment classification | S-05, S-06; `/segment-assessments` | DD-03, AD-04 | `segment_assessments` (versions, `unknown` band, first-invoice state; decider role by trigger) | T-3.2.2, T-3.3.2 | UT-10, IT-13, E2E-05 |
| MH-03 Versioned deadlines and provisions | S-04, S-06, S-14; `/calendar-versions`, `/provisions` | DD-03, AD-07, AD-11 | `calendar_versions`, `calendar_rules` (basis, candidates, discrepancy), `provisions`, `rules.valid_from`/`valid_to` | T-0.1.3, T-1.1.2, T-3.2.2, T-4.1.4 | UT-10, UT-13, UT-16, UT-18, E2E-08 |
| MH-04 Upload | S-07; `/uploads` | AD-03 | `uploads` unique hash; storage key scheme | T-3.1.1, T-3.1.3, T-2.2.6 | IT-03, IT-06, IT-08, IT-15 |
| MH-05 Mapping with confirmation and approval | S-08, S-12; `/uploads/{id}/mapping`, `/mappings/{id}/decision`, `/value-mappings` | DD-07, AD-06 | `column_mappings` (approved state), `value_mappings`; Reviewer or Owner approves | T-3.1.2, T-3.1.3 | UT-03, UT-08, UT-11, IT-02, E2E-01 |
| MH-06 Deterministic checks | S-09; `/runs` | AD-04, AD-07, AD-10 | `check_runs` (pins, input hash), `findings` (outcome, not-checked reason), `rules` | T-1.1.1, T-3.2.1 | UT-01 to UT-09, UT-12, UT-14 |
| MH-07 Fix list with evidence | S-10; `/findings` | DD-04 | `findings` (upload, sheet, row, column), `staged_rows` | T-3.3.3, T-4.1.2 | E2E-01, E2E-03, UT-15 |
| MH-08 Status never overstates | S-04, S-05, S-12 | DD-02, DD-06, AD-10, AD-11 | `readiness_snapshots` (`unchecked_blockers`, check constraint on Data-ready), `finding_exceptions`, the `entity_status` read function | T-1.1.5, T-3.2.3 | UT-11, UT-14, UT-17, IT-17, E2E-02 |
| MH-09 Cross-client dashboard | S-04; `/dashboard`, `/runs/batch`, `/dashboard/exports` | DD-01 | Indexes on snapshots and ASP status; the `entity_status` read function | T-3.3.1 | E2E-03, E2E-08, LOAD-02 |
| MH-10 ASP status and overlap | S-11, S-10, S-04; `/asp-status`, `PATCH /findings/{id}` | DD-03 | `asp_statuses`, `findings.asp_also_flagged` | T-3.3.4, T-3.3.3, T-3.3.1, T-0.3.3 | E2E-08 (overdue-first listing), metric M-03 |
| MH-11 Approved report | S-12; `/reports`, `/reports/lookup`, `/reports/{id}/delivered` | DD-05, DD-08, AD-04, AD-11 | `reports` (pins, reference code, immutability trigger); approve is Reviewer or Owner; `system_flags` | T-4.1.1, T-6.1.5 | IT-07, IT-17, E2E-04, OPS-06 |
| MH-12 Rule and calendar updates | S-14, S-04 banner; `/vendor/rule-packs/{code}/publish`, `/vendor/calendar-versions/{code}/publish` | AD-04, AD-07, AD-11 | `rule_packs`, `calendar_versions` (hash, status), `publications`; staleness derived, not stored | T-3.2.4, T-0.1.7, T-6.2.3 | IT-07, IT-12, IT-17, IT-21, E2E-02 |
| MH-13 Monthly cycle | S-13; `/cycles`, `/rejections` | DD-01 | `cycles`, `rejections` | T-4.2.1, T-4.2.2 | E2E-06 |
| MH-14 Audit, export, deletion | S-16; `/audit-events`, `/exports`, `DELETE /entities/{id}`, `/support-grants`, `/deletion-requests` | TRD §8.6 | `audit_events` insert-only, `deletion_requests`, `support_grants` | T-2.2.4, T-4.1.3 | IT-10, IT-14, IT-20, IT-21 |
| MH-15 Handoff pack | S-12; `/handoff-packs` | AD-09 | `files` purpose `handoff` | T-4.1.2 | UT-15, IT-19, E2E-01 |

Paid-pilot promise followed end to end: Decision §5.2 → MH-04 to MH-11 → S-07 to S-12 → role matrix → `uploads` to `reports` → T-0.3.2 by hand, T-3.1.1 to T-4.1.1 in the application → E2E-01. Failure scenario followed: PRD §7 False Ready → PRD §5 (unchecked blocker, derived staleness) → TRD §6.2 → S-08 approval, S-12 approval check → snapshot check constraint, pins, `entity_status` → T-3.2.3, T-3.2.4, T-6.1.5 → UT-11, IT-07, IT-17, E2E-02, OPS-06; before the application exists → T-0.1.7 and T-0.3.4.

## 5. Production risk register

All 22 apply; none is marked not applicable. Tests are defined in execution-plan.md section 8 and are `Not run`.

| ID | Risk | Impact for this buyer and data | Prevention | Detection signal | Test and expected outcome | Task |
|---|---|---|---|---|---|---|
| R-01 | Out-of-order or duplicate events overwrite a newer job state | A late "succeeded" from an old check run replaces a newer run's result, so a client that now fails shows its old Data-ready status | Compare-and-set on `state_version`; results written only by the current `attempt_id`; one current snapshot per entity | Count of discarded stale completions; snapshot whose run is not the latest | IT-04: state never regresses; stale completion discarded and logged. B1 2026-11-11: IT-04 (superseded attempt discarded, state never regresses), passed | T-2.2.5 |
| R-02 | A caller timeout prevents reconciliation with a valid later completion | The Preparer's browser gives up on a 200,000-line check; the run finishes but the fix list never appears, and the firm misses the 2-day turnaround | Requests return 202 and poll; lease and sweeper never fail a job whose attempt is live; completion accepted after the interface stopped waiting | Jobs succeeded but never read; queue age | IT-05: result visible on next read; superseded attempt discarded. B1 2026-11-11: IT-05 (result visible after the client stopped polling), passed | T-2.2.5 |
| R-03 | New utilities duplicate behaviour already owned by shared code | A second TRN validator or a second status function disagrees with the first; the dashboard and the report show different statuses for one client | One rule engine, one status function, one calendar lookup in `packages/rules`; review checklist item | Lint for duplicate validators; differing status in two places | ARCH-01 plus UT-11 run through both API and worker entry points give equal results. B1 2026-11-11: ARCH-01; UT-11 rows through the API and worker (`test_readiness_flow.py`), passed | T-2.1.1 |
| R-04 | Applications import private code across architectural boundaries | The web app reaches into worker parsing code; a parser change breaks sign-in pages during a deadline week | Import-boundary lint; packages expose a public interface only | CI failure | ARCH-01: seeded cross-app import fails. B1 2026-11-11: ARCH-01 (seeded cross-app import fails), passed | T-2.1.1 |
| R-05 | Tenant enforcement is scattered or bypassed through APIs, workers, caches or files | One firm sees another firm's client names, TRNs and prices: the end of trust in a product sold to tax agents | Row-level security plus service-layer checks; one tenancy session for API and worker; firm-prefixed object keys; no cache | Audit events for denied cross-firm access | IT-01 across every endpoint, file path and worker context: 404 and 0 rows. B1 2026-11-11: IT-01 partial (14 API routes, worker context, no-context reads; files and exports not built), passed | T-2.2.2, T-5.1.1 |
| R-06 | Workers copy configuration and utility modules, causing behavioural drift | The worker's copy of the size limit or the Asia/Dubai date helper differs from the API's; a deadline shows a day late | Single `packages/core/config` and date helper; no copies | Lint for duplicated module names | ARCH-01: a copied config module in `apps/worker` fails; UT-13 run in the worker. B1 2026-11-11: ARCH-01 (copied config module in `apps/worker` fails); UT-13 in the worker Not run, passed | T-2.1.1 |
| R-07 | Worker logging imports web-only modules and crashes during startup | The worker dies on start after a deploy; uploads queue up unprocessed during a pilot | `packages/core/logging` has no web imports; worker start test in CI | Worker heartbeat missing; `/readyz` red | ARCH-01 web import fails; OPS-04 start check includes the worker. B1 2026-11-11: ARCH-01 (web import in `packages/core` fails); worker import test; OPS-04 local, passed | T-2.1.1, T-2.1.2 |
| R-08 | ORM declarations omit indexes or constraints present in migrations | The unique index that stops duplicate uploads, or the one-current-snapshot index, exists in one path only; duplicates appear in a rebuilt environment | Parity check between migration-built and model-built schemas | CI diff | IT-11: schemas equal. B1 2026-11-11: IT-11 parity part (equal; seeded drift detected), passed | T-2.2.1 |
| R-09 | Interrupted migrations or backfills cannot resume safely | A fingerprint backfill on `findings` stops halfway; exceptions no longer match their findings and reappear as open blockers, or vanish | Backfills as resumable jobs with a progress row, outside schema transactions | Progress row not at 100% | IT-11: interrupted at 40%, resumes without duplicates | T-2.2.1, T-5.1.3 |
| R-10 | Merged branches introduce conflicting migration order | Two developers add migrations for `rule_packs` and `calendar_versions`; deployment fails on the day a new MoF version must be loaded | Single-head CI check; rebase before merge | CI failure on two heads | IT-11: two heads fail. B1 2026-11-11: IT-11 heads part (two heads detected), passed | T-2.2.1 |
| R-11 | Index creation locks busy production tables during deployment | An index build on `findings` blocks check runs while firms are uploading before 31 March 2027 | Concurrent builds; 5-second lock timeout; deploy outside the UAE working day | Lock wait alerts | IT-11: no statement waits beyond 5 seconds | T-2.2.1, T-5.1.3 |
| R-12 | Correlation IDs disappear across jobs and retries, or sensitive data leaks into logs | A failed run cannot be traced for the firm; or customer names and TRNs from uploads sit in logs kept outside the retention rules | Correlation identifier on request, job and retry; log allow-list of identifiers and counts | Logs without identifier; pattern scan for 15-digit numbers | IT-10: 0 matches for fixture TRN and name; one identifier end to end. B1 2026-11-11: IT-10 (0 matches for fixture TRNs and names; one correlation identifier on request, job and log), passed | T-2.2.4 |
| R-13 | Upload keys collide or fail to isolate tenant, source and purpose | Two firms upload `customers.xlsx`; one overwrites the other, or a handoff pack is built from the wrong client's file | Generated keys with firm, entity and purpose prefixes; unique `storage_key` | Constraint violations | IT-15: distinct keys per firm and purpose. B1 2026-11-11: IT-15 (distinct keys under each firm prefix and purpose), passed | T-2.2.6 |
| R-14 | Temporary uploads survive retention expiry or failed cleanup | Client invoice exports and expired exports remain after the period promised in the pilot agreement | `expires_at`; sweeper with counts; orphan scan; alert | Rows past `expires_at`; sweeper failure | IT-09: expired and orphaned objects removed; failure alerts and recovers | T-2.2.6 |
| R-15 | Missing persistent volumes cause data loss after service recreation | Database and files are managed services, so the exposure is the proxy's certificate data and local development volumes; losing certificates takes the site down in a deadline week | Named volumes; start check; data never on the VM disk | Start-up check; certificate expiry alert | OPS-03: recreate containers, everything intact | T-2.1.4 |
| R-16 | Generated file links use internal hosts or `localhost` behind a public proxy | An invitation or a report link in the monthly summary points at an internal address; the Reviewer cannot open it | One validated `PUBLIC_BASE_URL`; files streamed through the API | Start refusal; staging link check | OPS-05: public HTTPS host in email and download; bad value stops start | T-2.1.4 |
| R-17 | Local dependencies and workers lack a reliable single startup command and health checks | A developer tests uploads with no worker and believes parsing works; the founder cannot restart the stack alone during a pilot | `make dev` waits for every service; readiness covers database, storage, migrations, worker | Command exit code | OPS-04: healthy in 3 minutes; clear failure with the database stopped. B1 2026-11-11: OPS-04 local (`make dev-check` ready in 1.1 s; unreachable database named), passed | T-2.1.2 |
| R-18 | Browser Back, refresh or deep links lose the user's result or task state | A Preparer 60 findings into a filtered fix list presses Back and loses position; a partner's emailed link to a client opens the dashboard instead | Filters, cursor and open finding in the URL; server jobs; deep-linkable routes; return URL after sign-in | Front-end error reports; pilot questions | E2E-03, E2E-07 | T-3.3.1, T-3.3.3 |
| R-19 | Bulk processing skips files, hides partial failures or duplicates successful work on retry | Three exports are uploaded and the invoices file fails silently; the client shows few gaps because invoices were never checked. Or a batch re-run of stale clients repeats completed ones | Per-file and per-entity states; totals must equal the count; retry selects failed only; hash-unique uploads; "Data incomplete" status when a dataset is missing | Totals mismatch; uploads not terminal in 15 minutes (M-10) | IT-06: 3 parsed, 1 rejected, retry touches 1; per-entity batch outcomes. B1 2026-11-11: IT-06 partial (FX-A 3 parsed, bad files rejected with reasons; retry and batch re-run not built), passed | T-3.1.1 |
| R-20 | Unclear labels, icons, stale routes or broken links misdirect users | "Ready" is read as "the ASP will accept it"; "Appointed" is confused with "Onboarded"; a link in an old report leads nowhere | Fixed vocabulary (design §8); "Data-ready" with pack version; icon with word; route table and link check | Link-check failures; questions logged in pilots | NAV-01; A11Y-03 greyscale review | T-5.1.6 |
| R-21 | Unrequested features consume effort without a requirement or pilot need | Time goes to connectors, XML generation or ASP formats while the decisive question (will a firm pay for month 3) stays open and cash falls as in Decision §7.5 | Every pull request cites an MH, R or task; non-goals with admission evidence (PRD §2); weekly triage | Pull requests without a reference | GOV-01 | T-2.1.3, T-6.2.4 |
| R-22 | Misnamed, duplicate or stale branches obscure the active work or endanger unmerged changes | A rule-pack correction for a new PINT AE release sits on an old branch and never reaches the pilot firms | Protected `main`; `type/T-x.y.z-slug`; merged branches auto-deleted; weekly report | Stale-branch report | GOV-02 | T-2.1.3, T-6.2.4 |

R-05's cache clause becomes live if a cache is added; R-16 widens if AD-03 changes to pre-signed links; R-15 widens if the database or files move onto the VM.

## 6. Findings register

Reserved for the independent reviewer. IDs `F-001`, `F-002`, …. The author records the fix; the reviewer records the retest.

Round 1, independent reviewer, 2026-11-10. Evidence and impact are shortened from the reviewer's note. Owner of every fix: Author A. Fixes made 2026-11-10. The last column for F-001 to F-019 is the independent reviewer's round 2 verdict of 2026-11-10, copied from the reviewer's records (`pint-ae-readiness-round2.md` and `pint-ae-readiness-verdicts.json` in the lead's coordination folder), not the author's opinion. F-020 and F-021 were raised in round 2 and fixed afterwards; no further round is planned, so their retest is pending.

| ID | Severity | File | Evidence | Impact | Owner | Fix made | Files changed | Retest condition | Retest result (independent reviewer, round 2) |
|---|---|---|---|---|---|---|---|---|---|
| F-001 | Blocker | PRD §5, MH-05, MH-08; schema; UT-03, UT-11; design S-08 | A field marked "not in this file" left its rule unrun and the client could reach Data-ready | False Ready | Author A | Lead ruling applied: `not_checked` on a blocker rule is an open blocker; new status "Checks incomplete"; score denominator defined; snapshot `unchecked_blockers` with a check constraint; no exception allowed on an unchecked result; S-08, S-10, design copy agree; UT-03, UT-11, E2E-02, IT-19 cover it | PRD, schema, App-flow, design, execution-plan, CLAUDE | PRD §5/MH-08 block Data-ready on any unchecked blocker; UT-11 and E2E-02 carry the case; UT-03 and S-08 agree | Closed, part open: outcome of RC-11 'manual review' rows (type codes 389, 261) is undefined, so whether they block Data-ready is not stated |
| F-002 | Major | PRD §7; App-flow S-08, S-12; schema §4 | The wrong-column mistake had no reviewer | A Preparer alone could mis-map a checked field | Author A | Column mappings need Reviewer or Owner approval before any report approval; S-12 shows mappings with samples; `column_mappings.approved_*`; permission row; IT-02 case; PRD §7 corrected | PRD, App-flow, schema, TRD, execution-plan | Reviewer approval in S-08, schema and IT-02 | Closed |
| F-003 | Major | TRD §6.2, AD-10; schema; PRD §5; tests | Staleness depended on a job; no fault test; no 45-day mechanism; incident steps untasked; sent PDFs | Old Data-ready rows and reports could stand | Author A | Staleness and supersession derived on every read (AD-11, view `entity_status`, no stored flag); job reduced to notices; IT-17 fault test; UT-17 for 45 days; T-6.1.5, `system_flags`, OPS-06 for the incident procedure; reports carry a reference code and a currency lookup. Open part: a PDF already sent cannot change; the firm must re-issue | PRD, TRD, schema, App-flow, execution-plan | Derived staleness plus fault test; 45-day test; incident task and test; report currency check | Closed, part open: a PDF already sent cannot be recalled; the firm must re-issue |
| F-004 | Major | MH-03, MH-09, MH-10; S-04; design; Decision §3; UT-10 | SEG-U described four ways; no place in the sort | A possibly overdue client could sit undated | Author A | One rule in Decision §3: both outcomes shown, earliest possible date governs sort and days-left; government entity of unknown Revenue is SEG-G; SEG-N stored as "before first invoice"; no Revenue is invented; UT-10 and E2E-08 | Decision, PRD, App-flow, design, schema, execution-plan | One SEG-U rule everywhere; sort test including SEG-U | Closed |
| F-005 | Major | Decision §3; schema; T-1.1.2; UT-16 | CAL-n used both for calendar versions and for provisions; no home for date-bound provisions | Next version would collide; rules could not be date-bound | Author A | CAL-1, CAL-2 are calendar versions only; provisions renamed PRV-1 to PRV-4; table `provisions`, `rules.valid_from`/`valid_to`, `calendar_rules.deadline_basis`; UT-18 boundary test for PRV-2 | Decision, PRD, schema, execution-plan | Separate IDs; stated home; one boundary test | Closed |
| F-006 | Major | Decision §1, §4, §10 | Wafeq's API route for existing ERPs omitted; Zoho Practice unmentioned | Gap overstated | Author A | Wafeq page re-opened: API route recorded with no price, no named systems, no described test facility; gap restated as pre-contract check, Excel-kept books and cross-ASP view; SR-2 question covers API-connected clients; Zoho Practice and Accountant Program recorded as not read | Decision | §4 records the API product; gap and SR-2 cover it; Zoho Practice noted | Closed |
| F-007 | Major | Decision §12, §13; T-0.1.2, T-0.2.1 | No UAE rule on cold email, calls or personal data cited | The only channel may be unlawful | Author A | Primary texts attempted and blocked (federal legislation site 403); instruments named and labelled unverified; legal questions LQ-1 to LQ-5; T-0.1.2 acceptance requires written clearance per channel before T-0.2.1; cold calls held; consequence for the funnel stated. **Open:** the answers | Decision, execution-plan, PRD | Rules named with status; legal clearance gates the first send | Open by design: lawfulness of cold email, LinkedIn and calls is unknown until written answers to LQ-1 to LQ-5 exist; first send is gated on them |
| F-008 | Major | T-0.2.3, T-0.3.2, T-2.1.4; Decision §11 | Real files handled in Phase 0 with no store or procedure | Client data uncontrolled | Author A | T-0.1.5 creates the UAE-region store and handling procedure with acceptance checks before any file; T-0.2.3 depends on it; Decision §11 item 4 made a gate tied to LQ-4 | execution-plan, Decision | Phase 0 store task before T-0.2.3; decision 4 resolved or gated | Closed |
| F-009 | Major | T-0.1.3, T-1.1.2, T-1.1.3, T-6.2.3 | Fixture used before it existed; rule watch only in Phase 6; no second check of hand work | False Ready during hand delivery | Author A | T-0.1.6 builds FX-A and FX-B in Phase 0; T-0.1.7 weekly watch from week 1; calendar sheet and T-1.1.2 second-person check; T-0.3.4 independent check of every hand report | execution-plan, Decision | Fixtures and watch in Phase 0; independent checks | Closed |
| F-010 | Major | Decision §5.2, §12; M-04; MH-15; schema; T-0.3.2 | Turnaround promise unmeasurable and unachievable in a burst; free check under-costed; handoff pack promised but P1 | Refunds and missed promise | Author A | Intake slots (10 entities per 2-business-day window) written into the offer; UAE business day defined; M-04 fields `intake_slot_at`, `intake_complete_at`, `delivered_at`, `business_holidays`, UT-19; free check costed at 4.5 h; refund and capacity cases in Decision §7.6; handoff promise conditional and MH-15 raised to P0; application-pilot criterion defined. **Open:** refund rate and holiday list are unsourced | Decision, PRD, schema, App-flow, execution-plan | Capacity and refund case; hours corrected; M-04 defined with fields and test; handoff aligned | Closed, part open: refund rate and UAE holiday list are unsourced |
| F-011 | Major | Decision §7.1, §7.5; execution-plan §6; TRD §7 | Build cost absent from cash; sales tools possibly counted twice | Cash need understated | Author A | Build valued at the plan's 412–644 h: AED 109,642.75–171,383.33; month-12 cash with build shown in §7.6; founder-build alternative stated; 3,200 composition reconciled, sales tools only in acquisition | Decision, TRD, execution-plan | §7.1 values the plan's hours; build in cash view; 3,200 reconciled | Closed |
| F-012 | Major | TRD §5.1, §11; App-flow; schema; SC-06 | Endpoints missing for many screen actions; vendor identity unspecified; publication control inconsistent | Routes escape the permission suite | Author A | Endpoint table rebuilt per screen action with a screen column; `vendor_users`, support session, read-only role (AD-12); publication control stated once as two-step, not two-person, with `publications`; IT-21; SC-06 re-run and its earlier "Pass" withdrawn | TRD, schema, App-flow, execution-plan, this file | Endpoint list complete; vendor identity and grant path; publication control consistent | Closed |
| F-013 | Major | TRD §8.1, §8.8; S-01, S-02; schema | No recovery flow; V3, V4, V13 not selected | Locked-out Owner; control listed without design | Author A | S-18 and four recovery cases; recovery codes for all users; tables `recovery_codes`, `password_resets`, `owner_resets`; IT-18; ASVS 6.4.4, 6.5.1–6.5.3, 3.3.1, 3.3.2, 3.3.4, 3.4.1, 3.4.3, 3.5.1, 4.1.1, 4.1.3, 4.2.1, 13.3.1, 13.3.2 read and selected. **Open:** recovery proofing is no stronger than the emailed invitation | TRD, App-flow, schema, design, execution-plan | Recovery in App-flow, API, schema and a test; V3/V4/V13 selected or not met | Closed, part open: recovery proofing is only as strong as the emailed invitation; SRC-22 chapter list not extended |
| F-014 | Major | design §4, §7, §8; A11Y tests | Upload and mapping withheld below 768 px, so unusable at 400% zoom; icon rule inconsistent; criteria untested | AA target missed by design | Author A | Upload and mapping work at 320 CSS px as stacked cards; nothing withheld; icons always labelled; 1.4.10 mapped to S-07, S-08, S-10; A11Y-05 to A11Y-07 added and every mapped criterion assigned to a test | design, App-flow, execution-plan | S-07/S-08 usable at 320 px; icon rule consistent; tests cover every criterion | Closed |
| F-015 | Minor | Decision §5.1, §6, §12 | Brief items dropped silently | Fidelity | Author A | All listed in Decision §13 as not adopted or not used, with the reason | Decision | Listed in §13 | Closed |
| F-016 | Minor | Decision §1, §4 | "Pays its ASP little or nothing" was inference | Overstated free floor | Author A | Sentence labelled [A] and limited to transaction charges; plan prices stated; MD 168 cited as read by the reviewer, not the author | Decision | Labelled and matched to source | Closed |
| F-017 | Minor | Decision §7.3, §7.5, §9 | 42.68; 4,536 against 4,500; no false-stop figure for revised SR-1 | Small | Author A | 42.67; the AED 36 explained as rounding of 1,785.71 to 1,800; SR-1 false-stop stated as not computable, bounded 0.023 to 0.108 | Decision | Corrected or noted | Closed |
| F-018 | Minor | schema | No seller address or registration type; no logo field; role rule as CHECK | Seller checks had no data | Author A | Seller profile fields on `client_entities`, entered on S-05, sourced from licence and EmaraTax profile; `firms.logo_file_id`; role rule moved to service layer and trigger | schema, PRD, App-flow | Fields or source named; rule moved | Closed |
| F-019 | Minor | verification §4; PRD §9 | MH-10, MH-15, MH-14 without asserting tests; no primary metric | Trace gaps | Author A | E2E-08, IT-19, IT-20 added and traced; M-02 marked primary | PRD, execution-plan, this file | Tests added; M-02 decisive | Closed |

| F-020 | Major (regression) | Decision §7.5, §9, §12; execution-plan M0.1, T-0.2.1 | Outreach still began 16 November 2026 although the legal answers and the file store now precede the first send; SR-1's sample depended on that start; no cost for the legal answers | The stop rule would fire because of the gates, not the product | Author A | Plan re-dated from the gates: earliest first send 14 December 2026 [A]; SR-1 counted at day 77 after the first send (28 February 2027), recount day 91 (14 March), SR-4 day 44 (26 January); last permitted first send 11 January 2027; false-stop 0.108 on the re-dated count and 0.641 if 31 January were kept; AED 10,000 legal placeholder in startup cost and a month 0 in the cash table; Decision §1 says plainly that little of the demand window remains | Decision, PRD, execution-plan, this file | Decision states start date, SR-1 date and sample under the gates and names the legal cost | Closed, part open: execution-plan section 1 diagram still read "Gate: 31 Jan 2027" (independent reviewer, final retest 2026-11-10, `pint-ae-readiness-round2.md`; verdict transcribed by the lead). The lead corrected that node to 28 Feb 2027 afterwards; that edit was not re-reviewed |
| F-021 | Minor (regression) | PRD §5, MH-03, MH-12; TRD §6.3; IT-13, UT-08; schema; Decision §13 | Leftover wording conflicts | Documents disagreed | Author A | A calendar change supersedes reports and never makes a result Stale (PRD §5, MH-03, MH-12, TRD §6.2, §6.3); IT-13 expects derived Stale; UT-08 expects "not checked"; `grace_period` and `manual_review` added to the PRD outcome list; SRC-22 lists V3, V4, V13 | PRD, TRD, execution-plan, schema, Decision | Wording aligned | Closed (independent reviewer, final retest 2026-11-10, `pint-ae-readiness-round2.md`; verdict transcribed by the lead) |

After round 2, for the open part of F-001: self-billed records (codes 389, 261) now have the outcome `manual_review`, which blocks Data-ready until a Reviewer resolves it (PRD §5, RC-11, schema, S-10, UT-11); closed at the final retest (independent reviewer, final retest 2026-11-10, `pint-ae-readiness-round2.md`; verdict transcribed by the lead).

Nothing is disputed. Reviewer's fresh-reader gap 6 (which calendar a Stale row's date comes from) is answered in PRD MH-03 and S-04: always the current published calendar.

### 6.1 Author self-check log

Run on 2026-11-10 with a script kept outside the repository. These are the author's checks, not review findings.

| ID | Check | Result |
|---|---|---|
| SC-01 | Exactly ten required files, nothing else | Pass |
| SC-02 | Every relative link resolves to a file and, where given, a heading anchor | Pass |
| SC-03 | Every MH, S, AD, DD, T, UT, IT, E2E, LOAD, OPS, A11Y, R, RC, SR and M identifier that is referenced is defined once | Pass |
| SC-04 | MH-01 to MH-15 each have a row in section 4 | Pass |
| SC-05 | R-01 to R-22 each have a row whose task IDs exist in execution-plan.md | Pass |
| SC-06 | Screens in App-flow.md, endpoints in TRD.md, tables in schema.md and tasks agree with the matrix | First run recorded "Pass" on a check that compared only table and task names; the reviewer found missing endpoints (F-012). Re-run after the fix with every screen action compared by hand against TRD §5.1: Pass |
| SC-07 | Economics re-run: gross profit 557.15; payback 3.23; break-even 8 and 43 (42.67); ramp table with month 0; one-off case; CAD conversions; 111.3 h and loaded cost 6,193.38; build 109,642.75–171,383.33 | Pass after round 2 |
| SC-08 | Binomial: 0.108 at 600 closed contacts, 0.177 at 500, 0.282 at 400, 0.641 at 200; 0.564 pass probability at half the close rate; day and date arithmetic from a 14 December 2026 first send | Pass after round 2 |
| SC-09 | Estimate sums: phases total 412–644 hours | Pass after round 1 |
| SC-10 | Highest-consequence failure named identically in PRD.md, CLAUDE.md and this file | Pass |
| SC-11 | No credentials; examples synthetic; all diagrams Mermaid | Pass |
| SC-12 | Word count against the 16,000–20,000 target | Over target and further over after the round 1 fixes; see section 8 |
| SC-13 | Round 1: reviewer's recalculation and integrity scripts re-run against the fixed files; own link, ID, matrix and risk checks re-run | Pass; the reviewer's script still prints the round 0 phase list (400–628), which the fixes changed to 412–644 |

## 7. Open items that documents cannot close

| Item | Needed evidence | Owner |
|---|---|---|
| Willingness to pay | Paid pilots (M-01) | Founder |
| Whether the ASP already covers the work | SR-2 answers; M-03 | Founder |
| Whether the monthly job is wanted | Month-3 payments (M-02); cycle use (M-07) | Founder |
| Distinct ICP firms | T-0.1.1 count | Founder |
| Whether RP-1's checks predict ASP acceptance | M-08 from pilots; comparison with an ASP's test results | Founder, pilot firm |
| Effective dates of PINT AE releases | A statement from MoF or OpenPeppol | Founder |
| Lawfulness of cold email, LinkedIn messages and calls to UAE tax agents; use of FTA directory contacts; processing client data with access from Canada; the "not an ASP" wording | Written answers to LQ-1 to LQ-5 (T-0.1.2) | Lawyer |
| Refund rate; UAE public-holiday list; second checker | Pilots; an official holiday announcement; founder decision | Founder |
| What Wafeq's API route costs and tests before go-live; what Zoho Practice shows per client | The vendors' pages or a sales answer | Founder |
| ASVS and WCAG conformance | Testing of a built application | Developer |

## 8. Outstanding items

| Item | Why open | Next step |
|---|---|---|
| Recurring job has no evidence | Decision §5.3 | Gate C |
| Little of the demand window is left after the gates (F-020) | First send 14 December 2026 at the earliest; decision 28 February 2027; month-3 evidence after 31 March 2027 | Founder decisions 9 and 10; do not start after 11 January 2027 |
| Legal cost unknown (F-020) | AED 10,000 is a placeholder | Obtain a quote in week 1 |
| One diagram date corrected after the final retest (F-020 leftover) | Edit made by the lead, not re-reviewed | None; recorded for accuracy |
| Refund rate and UAE holiday list unsourced (F-010) | No source | Pilots; official announcement |
| Outreach channel not legally cleared (F-007) | Primary texts blocked; LQ-1 to LQ-3 unanswered | T-0.1.2 before any send |
| Client-data handling from Canada not cleared (F-008) | LQ-4 unanswered | T-0.1.5 before any file |
| Build cost AED 109,642.75–171,383.33 is unfunded in the model (F-011) | Decision §7.6 | Founder decision 7 |
| Sent PDFs cannot be recalled (F-003) | Outside the product | Firm re-issues from "Reports to re-issue" |
| Recovery proofing equals an emailed invitation (F-013) | TRD §8.1 | Accept for the pilot or add stronger proofing |
| Hand-delivery capacity below expected demand (F-010) | Decision §7.6 | Slot schedule; internal runner |
| Wafeq API route price and Zoho Practice not read (F-006) | Linked pages not opened | Read before the first discovery call |
| Base case never reaches break-even | Decision §7.5 | Founder decision on partner channel or project pricing |
| SEG-L date conflict between MoF guideline and decision | Decision §3 | Watch for a corrected guideline (T-0.1.7); no pilot impact |
| Sources not opened | Decision §13 list | Read before relying on penalties, ASP eligibility, data-protection duties or competitor claims |
| Brief items not reconciled | Lead cost per 100 prospects against the 30-day sales budget; 30-day cash budget split; "AED 3,000 MRR" in week 4; 18-day build; 80 founder hours against the 111.3 the offer needs | Founder to confirm the author's treatment |
| ASVS 5.4.3 and 8.4.2 | Not met in the planned MVP (TRD §8.8) | Accept or schedule |
| Margin-scheme tax category code | Not confirmed at source (PRD §6) | Read the PINT AE code list before T-1.1.1 |
| Word count | Completeness was preferred to the target, as the guide allows | Reviewer to say what can go |


## 9. B1 build record (2026-11-11)

**Authorisation.** On 2026-11-11 the owner authorised implementation in all ten repositories at once, before this product's Phase 0 sales gate (gates A and B, T-0.1.2, T-0.1.5) has passed. Decision.md is unchanged. Only synthetic fixtures were used; no client file was accepted and no message was sent, so the CLAUDE.md rule on Phase 0 gates is not breached.

**Tasks implemented** (branch `feat/b1-foundation`): T-2.1.1 (layout, import-boundary check), T-2.1.2 (one start command with readiness, run directly without Docker), T-2.2.1 (migration 0001, models, parity and single-head check), T-2.2.2 (row-level security, `pintae_app` role, tenancy session, 404 with audit), T-2.2.4 (audit events, structured logs with correlation identifiers), T-2.2.5 (job table, claim, leases, compare-and-set, worker), T-2.2.6 partial (storage-key builder and local object store; expiry sweeper not built), T-3.1.1 (upload endpoint, type/size/content checks, hashes, per-file states, staged rows), T-3.1.2 (dictionary mapper, fingerprints, reuse, "not in this file", confirm, Reviewer approval, value tables; no screens), T-3.2.1 (rule engine and RP-1 as data with golden fixtures; the founder's CLI runner not built), T-3.2.2 (segment function, calendar lookup, Asia/Dubai dates), T-3.2.3 (status function, snapshots, staleness derived on read), T-3.2.4 (two-step publication, approval pin guard, approvals freeze; `notify_stale` notices not built because status never depends on them).

**Commands and results.** All from the repository root, after `make venv`.

| Command | Result |
|---|---|
| `make test` (drops and recreates the `public` schema of `pintae_test`, migrates to head, publishes CAL-1, CAL-2, RP-1, runs `backend/tests`) | 98 passed, 0 failed (60 unit, 38 integration) |
| `make lint` (ruff check and format check) | Pass, 0 findings |
| `make typecheck` (mypy strict, 55 files) | Pass, 0 errors |
| `make arch` (ARCH-01) | Pass, 0 violations |
| `make parity` (against `pintae_test`) | Equal, single head 0001 |
| `make dev-check` (clean `pintae_dev` schema) | Ready in 1.1 s: database, migrations, storage, worker heartbeat |
| `PINTAE_ADMIN_DATABASE_URL=...:5499/... make dev-check` | Exit 1, "not ready: database" |

**Test IDs that ran** (test files under `backend/tests/`):

| ID | Result | Where and scope |
|---|---|---|
| UT-01 to UT-09 | Pass | `unit/test_engine.py`; UT-09 includes a Hypothesis property test (150 examples); the RP-1 fixture suite also covers them |
| UT-10, UT-13, UT-16 | Pass | `unit/test_segment_calendar.py` |
| UT-11 | Pass | `unit/test_status.py` (all ten rows) and through API and worker in `integration/test_readiness_flow.py` |
| UT-12 | Pass | engine hash and repeat run through the worker |
| UT-14 | Pass | engine and API level; the expected text corrected from RC-04 to RC-06 (document change below) |
| UT-17 | Pass | function level and on read through the API with a moved clock |
| UT-18 | Pass | PRV-2 from CAL-2 provisions |
| IT-01 | Pass, partial | 14 routes return 404 with `{"reason": "not_found"}` and an audit event; worker session and no-context reads give 0 rows. Files, exports and support grants are not built |
| IT-02 | Pass, partial | 7 decision routes return 403 for a Preparer; cycle close and user reset not built |
| IT-03, IT-04, IT-05, IT-07, IT-08, IT-10, IT-13, IT-15 | Pass | `integration/` |
| IT-06 | Pass, partial | FX-A three files parsed, FX-E and other bad files rejected with reasons; retry and batch re-run not built |
| IT-11 | Pass, partial | parity equal, drift detected, two heads detected; interrupted backfill and concurrent index under load Not run |
| IT-12 | Pass | failing fixture, changed content under the same code and a wrong confirmed hash refused; valid pack published and entity read as Stale. The TOTP part of step 2 is not built |
| IT-16 | Pass, partial | disabled user and 31-minute idle session refused; sign-in without TOTP not built |
| IT-17 | Pass, partial | with no notice job at all: entity Stale, approved report Superseded, approval 409. The alert on a failed job is not built |
| ARCH-01 | Pass | three seeded violations each fail |
| OPS-04 | Pass, local | start command ready within 3 minutes; the database was not stopped (the build guide forbids touching the running service), an unreachable port was used instead |
| OPS-05 | Pass, partial | start refused for a non-HTTPS or local `PUBLIC_BASE_URL` outside local; email and download links not built |

E2E-02 (a) to (c) and the E2E-08 ordering were exercised at API and function level only; E2E-02 and E2E-08 stay `Not run` because they are browser tests. Every other ID stays `Not run`.

**Blocked or not built, and why.** T-2.1.3 (CI and branch protection need the GitHub repository settings and a push, which the lead does); T-2.1.4 (needs the UAE-region cloud account of T-0.1.5); T-2.2.3 (password, TOTP, invitations, recovery and vendor sign-in: out of B1 scope; tests seed hashed session tokens directly); T-3.1.3 and all screens (no frontend in B1); M3.3 onward. Not built inside implemented tasks: `notify_stale`, the sweeper, file downloads, exports, the handoff pack, PDF rendering.

**Document changes made in B1.** (1) execution-plan.md UT-14 expected outcome: RC-04 is the seller-profile rule, so the finding produced on the customer record is RC-06. (2) schema.md and execution-plan.md T-3.2.3: `entity_status` is a read function, not a SQL view, so the status logic exists once (R-03). (3) schema.md `findings`: `upload_id` nullable and `row_number` 0 for seller-profile findings; new reason `prerequisite_unresolved`; new `message`; reason required exactly for `not_checked`. (4) schema.md: `rule_packs.content`, `reports.printed_status`, one current `asp_statuses` row per entity, new global table `worker_heartbeats`; `staged_rows` partitioning deferred. (5) AGENTS.md state line, utilities index and command status; CLAUDE.md state line.

**Interpretations and gaps to review.** RC-17 "agree to 0.01" is implemented as equality at two decimals with half-up rounding [A], because UT-09 requires 10,500.01 against 10,500.00 to fail. RC-13 checks presence only; RC-15 runs on items, not lines; RC-19 does not check the free-zone beneficiary; RC-08's "UAE endpoint" applies only when an endpoint column is mapped. A value shaped like a code but not in the pack list fails, free text without an approved mapping is `not_checked` (this is how UT-03 and UT-08 are read). The RP-1 unit list is a subset of UNECE Rec 20/21 (a valid code outside it fails, the safe direction). A duplicate invoice number also fails RC-17 because the two invoices are grouped together. TRD section 6.2's `FOR SHARE` on current versions during approval was not implemented in the first B1 commit; fixed in round 1 (B1-009, below). The decision-role trigger covers deciders on six tables; the support session, read-only support role and vendor routes do not exist yet.


### 9.1 Fix round 1 (2026-11-11), after the independent B1 code review

Review: `_coordination/review/pint-ae-readiness-b1-round1.md` (2 blockers, 5 majors, 4 minors). The reviewer's scratch cases were run before and after the fixes, unchanged, from `backend/` with `PYTHONPATH=. .venv/bin/pytest -c pyproject.toml --rootdir=. -p no:cacheprovider -q -s <file>`. Those cases assert the behaviour the reviewer found, so after the fixes each defect case fails its old assertion and prints the corrected result. Before the fixes: A1 0 blockers; A2 0; A4 RC-08 not applied; A5 invoice out of scope; A6 only the `fail` stored; A9 SEG-N unknown "Before first invoice"; B1 Data-ready; B3 Data-ready and approval 200 before parse; C1 still Data-ready after CAL-3, and the re-run reused the old run. After the fixes: A1 RC-06 emirate `fail`; A2 RC-04 `not_checked`; A4 RC-08 `not_checked` on the invoice; A5 the invoice is in scope, with RC-21 `fail` on both customer rows, RC-21 `not_checked` on the invoice and RC-17 `fail`; A6 `fail` and `not_checked` both stored; A9 "First invoice date needed", passed; B1 Checks incomplete, printed "Checks incomplete"; B3 Stale (`upload_changed`) and approval 409 before parse; C1 Stale (`calendar_changed`), then a new run gives Gaps open. All cases the reviewer marked sound (A7, A8, A10, B2, B4 to B9) are unchanged.

| Finding | State | Fix | Permanent regression tests |
|---|---|---|---|
| B1-001 (blocker) | Fixed | Every run pins `calendar_version`, which is part of the input hash; execution applies the pinned calendar's provisions; `Versions` carries the calendar version, so a new calendar gives Stale (`calendar_changed`), and a re-run creates a new run | `integration/test_review_round1.py::test_c1_*`; `unit/test_review_round1.py::test_calendar_and_upload_changes_are_stale_reasons` |
| B1-002 (blocker) | Fixed | Records per dataset are stored with the run. A mapped required dataset with 0 rows gives Checks incomplete (`counts.empty_datasets`). New snapshot column `empty_datasets`, included in the Data-ready CHECK (migration 0002). The mapping response shows `data_rows` | `test_b1_header_only_*`, `test_b1_header_row_set_to_last_row_*`, `test_empty_required_dataset_*` |
| B1-003 | Fixed | Country is validated against ISO 3166-1 alpha-2 in RP-1. UAE spellings are normalised to AE, other free text needs a `country` value mapping, and an invalid code fails. The emirate is required whenever the resolved country is AE | fixture cases B1-003 (3); `test_a1_*`, `test_a2_*`, `test_country_code_validated_and_normalised`, `test_country_value_mapping_kind_is_accepted` |
| B1-004 | Fixed | Scope is decided per invoice. Conflicting rows for one customer ID stay in scope and fail RC-21 (new). An invoice matching them is in scope with RC-21 `not_checked` (`prerequisite_unresolved`). An unknown customer ID fails RC-21 | fixture case B1-004; `test_a5_*`, `test_identical_duplicate_*`, `test_invoice_customer_not_in_customers_file_fails` |
| B1-005 | Fixed | Staleness compares the run's upload ids with the newest received or parsed upload per dataset (`upload_changed`). Approval pins include uploads (409). A rejected re-upload changes nothing | `test_b3_*`, `test_rejected_reupload_*` |
| B1-006 | Fixed | RC-19 is a blocker (presence and 8-flag shape) per SRC-03 field 5 (28 Oct 2026); flag derivation stays a Reviewer judgement | fixture case B1-006; `test_transaction_type_code_is_blocking` |
| B1-007 | Fixed | RC-08 also runs on 480/81 invoices: with a readable single customer the customer-level check decides; otherwise `not_checked` (SRC-02 §18.2.1, 26 Oct 2026) | fixture case B1-007; `test_a4_*`, `test_tax_invoice_does_not_need_*` |
| B1-008 | Fixed | A non-fail finding's fingerprint carries its outcome, so `not_checked` and `fail` on different lines are both stored; fail fingerprints (exception keys) are unchanged | `test_a6_*` |
| B1-009 | Fixed | Approval takes a shared advisory lock, which publication takes exclusively, and the entity row lock (`FOR UPDATE`), which every pinned-version change takes (profile, segment, mapping, value tables, uploads, runs, exceptions, resolutions, worker parse). Pins are compared after both locks | `test_b1_009_*` (publication and entity update each time out while an approval holds the locks) |
| B1-010 | Fixed | SEG-N with an unknown or missing first-invoice state shows "First invoice date needed", is treated as passed and sorts as overdue, flag `first_invoice_date_needed`. Using uploaded invoice dates is not built | `test_seg_n_unknown_first_invoice_needs_a_date` |
| B1-011 | Fixed | The three `entity_status` "view" citations and the mypy file count corrected | n/a (documents) |
| Reviewer comparison: MF 24 | Fixed | RC-07 still accepts a TIN; new warning rule RC-22 records a TIN-only UAE business buyer (SRC-03 field 24) | fixture case MF 24; `test_tin_only_buyer_*` |
| Reviewer comparison: exactly AED 50M | Fixed | New band `eq_50m` gives SEG-U with both outcomes, the earlier SEG-L dates governing and flag `revenue_exactly_50m_sources_disagree` (SRC-02 §8.3 against SRC-24) | `test_revenue_exactly_50m_*` (unit and integration) |
| Reviewer observation: vendor credentials | Fixed | SELECT on `vendor_users` revoked from `pintae_app` (migration 0002) | `test_application_role_cannot_read_vendor_credentials` |
| A3 (endpoint marked absent) | Open, disclosed | RC-08 still applies to non-commercial buyers only when an endpoint column is mapped; not in the rulings | none |

RP-1 was corrected under the same code. It had been published only to the local and test databases, never outside them, so both were rebuilt; from now on any change is a new pack version (AD-07). The RP-1 fixture suite grew from 18 to 25 cases. Migration 0002 is the new head.

| Command (after round 1, from a rebuilt `pintae_test` and a rebuilt `pintae_dev`) | Result |
|---|---|
| `make test` | 122 passed, 0 failed (75 unit, 47 integration) |
| `make lint` | Pass, 57 files formatted, 0 findings |
| `make typecheck` (mypy strict, 57 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0002 |
| `make dev-check` | Ready in 1.1 s |

Documents changed in round 1: PRD.md (section 5 calendar, upload and empty-dataset staleness and the 45-day basis; MH-08; MH-12; RC-04, RC-06, RC-07, RC-08 and RC-19 rewritten; RC-21 and RC-22 added; gap note for MF 22–23, 34, 39 and 48–49), TRD.md (section 6.2 diagram and text, section 6.3 `run_checks` row), schema.md (`revenue_band`, `value_mappings.kind`, `check_runs.inputs`, `readiness_snapshots.empty_datasets` and its CHECK, the staleness derivation, the index citations, the `vendor_users` grant), Decision.md (a second recorded conflict in section 3; SRC-24 in section 13, opened by the reviewer on 2026-11-11 and not by the author), App-flow.md (S-06 band choices and SEG-N display), and this file (the citations and this section). These edits have not been re-reviewed.


### 9.2 Retest round 2 (2026-11-11) and the fixes after it

Reviewer's round-2 verdicts, copied unchanged from `_coordination/review/pint-ae-readiness-b1-verdicts.json`:

| ID | Reviewer verdict (round 2) |
|---|---|
| B1-001 | Closed |
| B1-002 | Closed |
| B1-003 | Closed |
| B1-004 | Closed |
| B1-005 | Closed |
| B1-006 | Closed |
| B1-007 | Closed |
| B1-008 | Closed |
| B1-009 | Closed |
| B1-010 | Closed, part open: uploaded invoice dates in the past do not flip SEG-N to Passed when the state is not_yet (disclosed) |
| B1-011 | Closed |
| B1-012 | Open (new, major): rules, calendar_rules and provisions have no immutability trigger and the status function reads severity and calendar data from them; an owner-role edit of RC-17 severity gave Data-ready on a wrong invoice total (N5) |
| B1-013 | Open (new, major): RC-08 does not apply when the buyer endpoint is absent or empty; a government buyer with no TIN and no legal registration passes, against IBR-149-AE (N4, the former A3) |

Fixes made after the round-2 retest, not yet re-reviewed. Each row is **fixed after retest**:

| ID | State | Fix | Regression tests |
|---|---|---|---|
| B1-012 | Fixed after retest | Migration 0003 adds trigger `pintae_published_child_immutable` on `rules`, `calendar_rules` and `provisions`. Once the parent pack or calendar is published or withdrawn, UPDATE and DELETE are refused, for the owner role too. INSERT is accepted only inside the publishing transaction. The status function also takes severity from the frozen, hashed `rule_packs.content`, not the child row. A change needs a new pack or calendar version | `integration/test_review_round1.py::test_b1_012_published_children_are_immutable_even_for_owner` (5 statements, including the owner edit of RC-17 severity) and `::test_b1_012_n5_severity_edit_cannot_produce_data_ready` |
| B1-013 | Fixed after retest | RC-08 applies to a UAE buyer whose endpoint is not TIN-based (IBR-149-AE). When the endpoint is absent or empty, it applies to every UAE (or unresolved-country) business or government buyer without a TIN-shaped TRN or TIN, and that buyer is checked, never skipped | `unit/test_review_round1.py::test_b1_013_*` (absent, empty, non-TIN endpoint, TIN endpoint, registration present) |
| B1-010 (open part) | Fixed after retest | Each run stores the earliest invoice issue date. An SEG-N entity whose uploaded invoices are dated on or before today shows "Passed: uploaded invoices are already dated" with flag `invoices_dated_before_today`, whatever state is recorded | `unit/...::test_seg_n_invoices_already_dated_is_flagged_passed`; `integration/...::test_b1_010_seg_n_with_past_invoice_dates_is_flagged` |

The reviewer's updated cases were run after the fixes. N4 and N5 now fail their gap-asserting assertions, which is the intended change: N4 gives RC-08 `fail` with the endpoint absent and with it mapped but empty, and in N5 the owner-role UPDATE is refused. All other reviewer cases pass. `make test` was then rerun to rebuild `pintae_test`.

| Command (after round 2, rebuilt `pintae_test` and `pintae_dev`) | Result |
|---|---|
| `make test` | 131 passed, 0 failed (77 unit, 54 integration) |
| `make lint` | Pass, 57 files formatted |
| `make typecheck` (57 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0003 |
| `make dev-check` | Ready in 1.0 s |

Not changed, as the reviewer noted: the worker's `run_checks` does not take the entity lock, and the timing-based lock tests may be flaky under CI load. Documents changed in this round: PRD.md (RC-08 row cites IBR-149-AE), schema.md (`rules`, `calendar_rules`, `provisions` immutability), App-flow.md (S-06 SEG-N display) and this section.

### 9.3 Retest round 3 (2026-11-11) and the fix after it

Reviewer's round-3 verdicts, copied unchanged from `_coordination/review/pint-ae-readiness-b1-verdicts.json`:

| ID | Reviewer verdict (round 3) |
|---|---|
| B1-001 | Closed |
| B1-002 | Closed |
| B1-003 | Closed |
| B1-004 | Closed |
| B1-005 | Closed |
| B1-006 | Closed |
| B1-007 | Closed |
| B1-008 | Closed |
| B1-009 | Closed |
| B1-010 | Closed |
| B1-011 | Closed |
| B1-012 | Still open: child rows now refuse owner UPDATE/DELETE/INSERT, but as the owner role a published RP-1 can be withdrawn, its content edited (RC-17 severity) and republished with plain UPDATEs, giving Data-ready on a wrong invoice total (X6); a withdrawn calendar can be set to draft, its children edited, then republished (X5); an UPDATE moving a child row to a draft parent is accepted (X4); TRUNCATE of the child tables is accepted (X3); content_hash is never verified against content |
| B1-013 | Closed |

Fix made after the round-3 retest, not yet re-reviewed:

| ID | State | Fix | Regression tests |
|---|---|---|---|
| B1-012 | **Fixed after round-3 retest, awaiting recheck** | Migration 0004. (1) `pintae_published_immutable` on `rule_packs` and `calendar_versions`: a published or withdrawn row never changes apart from published → withdrawn; withdrawn is terminal (no return to published or draft); `content`, `content_hash`, `created_at`, `published_at` and every other column are frozen; a draft is never published by UPDATE; DELETE refused. (2) `pintae_published_child_immutable` checks the OLD and the NEW parent, so a child row cannot be moved to a draft pack (X4). (3) `BEFORE TRUNCATE` statement triggers on `rule_packs`, `rules`, `calendar_versions`, `calendar_rules`, `provisions`, `publications` (X3); `publications` rows refuse UPDATE and DELETE. (4) UPDATE, DELETE and TRUNCATE revoked from PUBLIC, `pintae_app` and the owner role; the owner keeps `UPDATE (status)` on the two parent tables for withdrawal. (5) `calendar_versions.content` stores the calendar file; `readiness.load_pack` and the calendar loader recompute `content_hash(content)` and refuse a mismatch, and the calendar is built from its content with the child rows required to agree. (6) `publication.withdraw` is the status-only withdrawal; `publish_*` refuses a withdrawn code (`version_withdrawn`). (7) `/readyz` reports `reference_data` failed when the pack or calendar in force does not verify | `integration/test_reference_immutability.py`: `test_x6_withdraw_edit_republish_is_refused_and_wrong_total_is_not_data_ready`, `test_x5_calendar_status_flip_cannot_unlock_children`, `test_x4_child_row_cannot_be_moved_to_a_draft_parent`, `test_draft_cannot_become_published_by_update`, `test_x3_truncate_refused_for_owner_and_app_role` (6 tables × with and without CASCADE), `test_publication_records_and_parents_cannot_be_deleted_or_edited` (4), `test_privileges_revoked_for_app_role_public_and_owner`, `test_withdrawal_is_terminal_and_pinned_runs_stay_pinned`, `test_loaders_refuse_content_that_does_not_match_its_hash`, `test_readiness_check_verifies_reference_data` |

Reviewer's script `_coordination/review/pint-ae-readiness-b1-round3_adversarial.py`, run after the fix: 18 passed, 1 failed. The failure is `test_X3_owner_role_truncate`, whose assertion records the gap (it expects TRUNCATE to be accepted); all four TRUNCATE statements are now refused (`... is immutable reference data; TRUNCATE is refused`), which is the intended change. X4 is refused (`rules of a published rule_packs is immutable`), X5 is refused at the second step (`withdrawn CAL-2 is immutable and terminal`), and X6 is refused after the withdrawal (`withdrawn RP-1 is immutable`), so no wrong-total run was made. The earlier scripts (`-b1-adversarial_test.py`, `-b1-calendar_test.py`): 26 passed. `make test` was then rerun to rebuild `pintae_test`.

| Command (after round 3, rebuilt `pintae_test`) | Result |
|---|---|
| `make test` | 155 passed, 0 failed (77 unit, 78 integration) |
| `make lint` | Pass, 58 files formatted |
| `make typecheck` (58 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0004 |
| `make dev-check` | Not ready, by name: `reference_data: failed (calendar_content_hash_mismatch)`. `pintae_dev` holds CAL-1 and CAL-2 published before migration 0004, without `content`, and the verified loader refuses them, as intended. Rebuilding `pintae_dev` (drop and recreate its schema, then `make dev`) was not permitted in this session and is left to the lead |

Residual, by design: a superuser owner can still disable a trigger (DDL) or set `session_replication_role`; the test-suite cleanup does this for versions a test published. Documents changed: schema.md (reference-data lifecycle and guard, `calendar_versions.content`, `publications`), TRD.md section 7 (withdrawal), AGENTS.md (utilities index, `/readyz`) and this section.

### 9.4 Retest round 4 (2026-11-11) and the fix after it

Reviewer's round-4 verdicts, copied unchanged from `_coordination/review/pint-ae-readiness-b1-verdicts.json`:

| ID | Reviewer verdict (round 4) |
|---|---|
| B1-001 | Closed |
| B1-002 | Closed |
| B1-003 | Closed |
| B1-004 | Closed |
| B1-005 | Closed |
| B1-006 | Closed |
| B1-007 | Closed |
| B1-008 | Closed |
| B1-009 | Closed |
| B1-010 | Closed |
| B1-011 | Closed |
| B1-012 | Closed |
| B1-013 | Closed |
| B1-014 | New (major, regression): migration 0004 adds calendar_versions.content as NULL for calendars published before 0004 and the new guard forbids backfilling it; an upgraded database (pintae_dev included) fails reference_data with calendar_content_hash_mismatch, entity GET and run POST return 500, and re-publishing the same code does not repair it |
| B2-001 | New (major, feat/b2-local-auth 77bbadd): using a recovery code clears totp_confirmed_at and replaces the TOTP secret before re-enrolment is confirmed; if re-enrolment is abandoned, the password alone or the reset link alone reaches a full session with an attacker-bound authenticator |

Fix made after the round-4 retest, not yet re-reviewed (B2-001 is fixed on `feat/b2-local-auth`, section 10.1 there):

| ID | State | Fix | Regression tests |
|---|---|---|---|
| B1-014 | **Fixed after round-4 retest, awaiting recheck** | Migration 0004b (after 0004, so a database already at 0004 is repaired too) adds `calendar_versions.content_origin` and fills `content` once, only where it is NULL, idempotently and resumably, from the version's own child rows (`pintae_core.calendar_content.derive_missing_content`). The shipped file is used when it hashes to the stored `content_hash` and describes exactly those rows (`publication`, hash unchanged); otherwise the rows are rebuilt and hashed (`derived_from_rows`). The guard on `calendar_versions` is suspended for that transaction only; schema.md records why this data step is allowed. A version whose rows are not a valid, sourced calendar becomes `legacy_unverified`: `current_calendar` skips it, so no run newly pins it; results pinned to it read Stale with reason `calendar_legacy_unverified`; loading it returns 409, never 500. The loader's row rebuild is now the same function | `integration/test_calendar_backfill.py`: `test_backfill_uses_the_published_file_when_it_matches_hash_and_rows`, `test_backfill_derives_content_from_rows_when_the_file_differs`, `test_unverifiable_calendar_is_legacy_never_pinned_and_pinned_results_read_stale` |

Reviewer's scripts after the fix:
- `pint-ae-readiness-b1-round4_upgrade.sh`, run from a scratch copy with this branch's head (63a0cc4) in place of 2cbce9d and the B2 head (9e6d36c) in place of 77bbadd; the script itself is unchanged.
  - U1: a database built and seeded at pushed 63623c4 (0003) and then upgraded reports `reference_data: ok`, and CAL-1 and CAL-2 have content. The re-publish step returns the existing id. Its "backfill UPDATE" now writes content identical to what is stored, so the guard sees no change.
  - U2 and U3: the upgraded schema equals the fresh schema, including ACLs.
  - U4: fails at `invites` as before. This is the reviewer's demonstration that the old 0001 cannot build B2.
  - U5: the 0001 SQL is identical.
- `pint-ae-readiness-b1-round4_adversarial.py` together with the earlier scripts: 51 passed.
- `pintae_dev` was upgraded in place on `feat/b2-local-auth`, without dropping anything. Its migration 0006 repeats the same idempotent step, because 0005 was applied there before 0004b existed. CAL-1 and CAL-2 became `publication`, and `make dev-check` is ready in 1.1 s.

| Command (this branch, rebuilt `pintae_test`) | Result |
|---|---|
| `make test` | 158 passed, 0 failed (77 unit, 81 integration) |
| `make lint` | Pass, 60 files |
| `make typecheck` (60 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0004b |

Documents changed: schema.md (`calendar_versions.content_origin`, the 0004b data step and why it is allowed), AGENTS.md (utilities index), this section.

### 9.5 Retest round 5 (2026-11-11) and the fix after it

Reviewer's round-5 verdicts, copied unchanged from `_coordination/review/pint-ae-readiness-b1-verdicts.json`:

| ID | Reviewer verdict (round 5) |
|---|---|
| B1-001 | Closed |
| B1-002 | Closed |
| B1-003 | Closed |
| B1-004 | Closed |
| B1-005 | Closed |
| B1-006 | Closed |
| B1-007 | Closed |
| B1-008 | Closed |
| B1-009 | Closed |
| B1-010 | Closed |
| B1-011 | Closed |
| B1-012 | Closed |
| B1-013 | Closed |
| B1-014 | Closed |
| B2-001 | Closed |
| B1-015 | New (major): calendar_content.classify (0004b/0006) adopts edited child rows as derived_from_rows when the stored hash still equals the shipped file but the rows differ, rewriting content_hash; a CAL-2 SEG-S appoint_by moved to 2028-12-31 at the pushed 0003 head becomes verified content after upgrade (U6a, U6b); deleted provisions likewise (U6c) |

Fix made after the round-5 retest, not yet re-reviewed:

| ID | State | Fix | Regression tests |
|---|---|---|---|
| B1-015 | **Fixed after round-5 retest, awaiting recheck** | `pintae_core.calendar_content.classify` (used by 0004b, and on B2 by 0006) marks a pre-0004 calendar `publication` only when three things hold: the calendar file shipped in the repository for that code hashes to the stored `content_hash`; that hash also equals the `publications` row; and the calendar rebuilt from the stored rows is identical to the file in canonical form and hash. Every other case becomes `legacy_unverified`: no shipped file, a different hash, or rows that differ. Such a version is never newly pinned; results pinned to it read Stale (`calendar_legacy_unverified`); loading it returns 409, never 500; an operator publishes a new version from the shipped definition. `derived_from_rows` is no longer produced, and loaders treat it as unverified, so a database upgraded with the round-4 draft is safe too. `/readyz` reports `reference_data` failed with `newest_calendar_unverified:<code>` while the newest published calendar is unverified; this is the operator signal the reviewer asked for, replacing the silent fallback. Rule packs needed nothing: their content has been NOT NULL and hashed since 0001 | `integration/test_calendar_backfill.py`: `test_b1_015_rows_edited_before_the_upgrade_are_never_verified` (4 cases: the reviewer's SEG-S deadline moved to 2028-12-31, provisions deleted, a note edited, the stored hash changed); `test_b1_015_rows_backfilled_by_the_earlier_draft_are_read_as_unverified`; `test_backfill_untouched_calendar_matching_the_shipped_file_is_verified` (the untouched variant, verified) |

Reviewer's scripts after the fix (B1 head 2307e28; B2 head 18759a5, which merges it):
- `pint-ae-readiness-b1-round5_upgrade.sh`, run with `B1NEW=2307e28 B2NEW=18759a5` (its variables; the script itself is unchanged).
  - U1, U1b, U1c and the direct path in U3: `reference_data: ok`; CAL-1 and CAL-2 are `publication`, with the hash equal to the shipped file and to the `publications` row; SEG-S appoint-by reads 2027-03-31.
  - U6a, U6b, U6c and U6d: CAL-2 is `legacy_unverified` with content NULL; the current calendar is CAL-1; `calendar_by_code(CAL-2)` is refused with `calendar_legacy_unverified`; `reference_data` reads failed with `newest_calendar_unverified:CAL-2`.
  - U2 and U3: the upgraded schema equals the fresh schema.
  - U4: fails, as the negative control is meant to.
  - U5: the SQL is identical.
- `pint-ae-readiness-b1-round5_adversarial.py`, the round-4 script and the earlier scripts: 52 passed at each head.
- `pint-ae-readiness-b2-round5_security.py` at the B2 head: 9 passed.

| Command (rebuilt `pintae_test`) | `feat/b1-foundation` | `feat/b2-local-auth` |
|---|---|---|
| `make test` | 162 passed (77 unit, 85 integration) | 199 passed (92 unit, 107 integration) |
| `make lint` / `make typecheck` | Pass, 60 files / 0 errors | Pass, 71 files / 0 errors |
| `make arch` / `make parity` | 0 violations / equal, head 0004b | 0 violations / equal, head 0007 |
| `make dev-check` on `pintae_dev` (head 0007, CAL-1 and CAL-2 `publication`) | not applicable: `pintae_dev` is at a B2 revision | Ready in 1.1 s |

Documents changed: schema.md (`calendar_versions` verification rule, the reason the data step is allowed, the `/readyz` signal), this section. Not changed: the reviewer's minor notes stay open as notes. These are the half-finished Owner reset that keeps the old authenticator until the user re-enrols, and migrations that import `pintae_core.calendar_content` at run time.

## 10. B2 build record (2026-11-11): sign-in and local services without external accounts

Owner request of 2026-11-11, branch `feat/b2-local-auth` from `feat/b1-foundation` at `2cbce9d` (the B1-012 round-3 fix, section 9.3). Synthetic data only; no provider account, no secret in git (`backend/.env` is gitignored; `backend/.env.example` holds names only).

Tasks (execution-plan.md): **T-2.2.3** in part (password, TOTP, sessions, invitations, recovery codes, reset links, rate limits, role checks; not the Owner reset, vendor sign-in or support session), **T-2.2.6** in part (S3-API object store, key checks; no expiry sweeper), **T-4.1.2** in part (fix-list export with cell escaping; no dashboard export or handoff pack), **T-4.1.3** in part (invitations, user role change and disable; no grants, export or deletion).

Built:
- Sign-in as TRD 8.1 specifies (password plus TOTP, not an e-mailed link; AD-05): migration 0005 (`invites`, `recovery_codes`, `password_resets`, `files`, `auth_attempts`; session stages; TOTP enrolment and replay columns; security-definer lookups). `pintae_core.auth` and `pintae_core.identity`; routes in `apps/api/pintae_api/auth_routes.py`. The B1 bearer-token stand-in is gone from the application: `deps.actor` accepts only the `__Host-pintae_session` cookie of a `full` session plus the anti-forgery token on state-changing requests. In tests, seeded `full` sessions remain the test-only stand-in, sent through the same cookie and anti-forgery checks.
- E-mail through SMTP (`pintae_core.mail`), Mailpit at 127.0.0.1:1025 locally; production selects another SMTP server by settings only.
- Object storage through the S3 API (`S3ObjectStore`), MinIO at http://127.0.0.1:9000, bucket `pintae-dev`, region `us-east-1`; keys `firms/{firm}/entities/{entity}/source-{dataset}/{uuid}` and `firms/{firm}/generated/{purpose}/{uuid}` (R-13); no public URL and no presigned URL; generated files leave only through `GET /files/{id}` inside the tenancy session.
- `/readyz` checks the object store bucket through the store interface and the reference data (section 9.3). `scripts/create_firm.py` creates a firm and e-mails its first Owner's invitation (run once against `pintae_dev` and Mailpit: invitation received).
- Not built and why: vendor sign-in and vendor routes, support sessions (IT-21), Owner reset of a user and vendor Owner reset (IT-18 last two parts), secret store (13.3.1, 13.3.2): no design detail or account needed in B2 scope, recorded as next. OIDC is not in the design and is not needed.

Tests that ran (all against a freshly rebuilt `pintae_test`, Mailpit and MinIO running):

| Test | Command | Result |
|---|---|---|
| Unit: TOTP against the RFC 6238 SHA-1 vectors, drift window and replay; password policy and scrypt hashing; TOTP-secret sealing bound to the user; tokens and anti-forgery; recovery codes; UT-15 (`=HYPERLINK("x")` escaped); storage-key checks | `cd backend && .venv/bin/pytest tests/unit/test_auth.py` | Pass (14) |
| Sign-in end to end with Mailpit (`test_b2_sign_in.py`, 15 tests): invitation read from Mailpit, weak and breached passwords refused, enrolment, TOTP, new token on sign-in, anti-forgery, sign-out invalidates, re-sign-in, TOTP code refused on reuse; cookie attributes; expired and revoked invitations refused (410); only the Owner invites; absolute expiry, role change and disable end sessions, last Owner protected (IT-16); session of firm B refused on firm A's objects and anti-forgery token not transferable; cross-origin refused; account throttle after five failures and client throttle after 30 requests (429); five wrong codes end the pending session; password reset by mailed link still requires TOTP, link refused on reuse and after expiry, no mail for an unknown address (IT-18 first three parts); recovery code works once and forces re-enrolment (IT-18 recovery part); pending session expiry | `cd backend && .venv/bin/pytest tests/integration/test_b2_sign_in.py` | Pass (15) |
| Storage with MinIO (`test_b2_storage.py`, 2 tests): uploads stored under the firm, entity and purpose prefix and parsed by the worker from MinIO (IT-15 against MinIO), fix-list export stored under `generated/fix_list`, downloaded by its firm with the generator's content type, refused for another firm (404) and without a session (401), anonymous bucket and object reads refused by MinIO (403), test objects removed | `cd backend && .venv/bin/pytest tests/integration/test_b2_storage.py` | Pass (2); bucket checked empty of `firms/` objects afterwards |
| IT-01 and IT-02 extended to the new endpoints (export, file download, user change cross-firm → 404; invitations and users by Preparer or Reviewer → 403) | `cd backend && .venv/bin/pytest tests/integration/test_tenancy_and_permissions.py` | Pass (10) |

| Command (B2 head) | Result |
|---|---|
| `make test` (rebuilds `pintae_test`) | 187 passed, 0 failed (92 unit, 95 integration) |
| `make lint` | Pass, 69 files formatted |
| `make typecheck` (69 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0005 |
| `make dev-check` | Not ready, by name: only `reference_data: failed (calendar_content_hash_mismatch)`; database, migrations (head 0005 applied to `pintae_dev`), worker heartbeat and storage (MinIO bucket) report ok. Cause: `pintae_dev` still holds CAL-1 and CAL-2 published before migration 0004, without `content` (section 9.3). Rebuilding `pintae_dev` was not permitted in this session; after the lead drops and recreates its schema, `make dev` republishes the reference data |

OWASP ASVS 5.0.0 [S: SRC-22], requirement IDs as selected in TRD 8.8 (status column there). Implemented in B2: 6.2.1; 6.3.1; 6.3.3; 6.3.6; 6.4.3; 6.5.1, 6.5.2, 6.5.3; 7.2.1, 7.2.3, 7.2.4; 7.3.1, 7.3.2; 7.4.1, 7.4.2; 3.3.1, 3.3.2, 3.3.4; 3.5.1; 4.1.1 (downloads); 8.2.1, 8.2.2, 8.3.1, 8.4.1 for users and invitations (3.4.1 and 3.4.3 were already in B1). Partial: 6.2.12 (offline common-password set, not a breach corpus); 6.4.4 (recovery (a) and (b) only). Not implemented: 13.3.1, 13.3.2 (no secret store); 4.1.3, 4.2.1 (no proxy); 5.4.3 (antivirus); 8.4.2 (vendor access); 16.x only in part (sign-in results are audited, log controls unchanged from B1). These are selected controls, not a claim of ASVS compliance.

Document changes: TRD.md (5.1 rows and build note, 8.1 build detail, 8.8 statuses), schema.md (users, sessions, invites, recovery_codes, password_resets, files, new `auth_attempts`, sign-in functions, storage note), App-flow.md (S-02 activation signs in), AGENTS.md (state line, utilities index, commands, local environment), this section. Migration 0001 now carries its own frozen table lists instead of importing them from the models, so later tables (0005) do not change what 0001 does.

### 10.1 B2 fix after review round 4 (2026-11-11)

The round-4 verdicts are copied in section 9.4. Fix made after the round-4 retest, not yet re-reviewed:

| ID | State | Fix | Regression tests |
|---|---|---|---|
| B2-001 | **Fixed after round-4 retest, awaiting recheck** | A recovery code now gives only a restricted `enrol` session. Its sole permitted action is confirming a new TOTP secret, which is held in `users.totp_pending_secret_enc` (migration 0007). The confirmed secret, `totp_confirmed_at` and the other recovery codes stay valid until that confirmation. Confirming swaps the secret in, reissues the recovery codes and ends the sessions started under the old factor. `password_step` and `complete_reset` never create an `enrol` session: an account with no confirmed TOTP gets 403 `totp_enrolment_required` and no session, and the reset link is not used up. The fresh proof for enrolment is the recovery code itself or an Owner-issued invitation: the first invitation, or `POST /users/{id}/reset` (S-15, TRD 8.1 (c)). That reset ends the user's sessions, makes the password unusable and e-mails a new invitation tied to the user (`invites.user_id`). Accepting it sets a new password and requires TOTP enrolment in that same flow. An Owner cannot reset themself (409), and only an Owner can reset (403) | `integration/test_b2_sign_in.py`: `test_b2_001_abandoned_reenrolment_keeps_the_old_factor` (password-only path), `test_b2_001_reset_link_after_abandoned_reenrolment_still_needs_the_old_totp` (mailbox-only path), `test_b2_001_confirming_the_new_factor_replaces_the_old_one`, `test_b2_001_unenrolled_account_needs_an_owner_reset`, `test_b2_001_owner_reset_ends_sessions_of_an_enrolled_user` (IT-18 Owner reset); IT-02 includes the reset route |

Reviewer's scripts at this branch's head:
- `pint-ae-readiness-b2-round4_security.py`: 7 passed, S3b included. After the abandoned re-enrolment, the old authenticator still works. The password alone gives stage `password`, and the reset link gives stage `password`; neither path reaches a full session.
- `pint-ae-readiness-b1-round4_adversarial.py` together with the earlier scripts: 51 passed.
- The upgrade script: see section 9.4.

| Command (this branch, rebuilt `pintae_test`) | Result |
|---|---|
| `make test` | 195 passed, 0 failed (92 unit, 103 integration) |
| `make lint` | Pass, 71 files |
| `make typecheck` (71 files) | Pass, 0 errors |
| `make arch` | Pass, 0 violations |
| `make parity` | Equal, single head 0007 |
| `make dev-check` on `pintae_dev`, upgraded in place from 0005 (0006 repaired CAL-1 and CAL-2; 0007 added the B2-001 columns) | Ready in about 1 s |

The `make dev-check` row in section 10 ("Not ready … reference_data") is superseded by this result. Documents changed: TRD.md (8.1 detail, 5.1 build note, 6.4.4 status), schema.md (`users.totp_pending_secret_enc`, `invites.user_id`), this section.
