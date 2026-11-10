# CLAUDE.md — PINT AE Readiness Desk

Read [AGENTS.md](AGENTS.md) first; it is canonical. This file adds only what is specific to this product. No code exists; commands are proposed.

## The buyer's workflow

A managing partner of a Dubai or Sharjah bookkeeping firm must get 30–150 SME clients ready for mandatory e-invoicing. A Preparer uploads each client's customer, item and invoice exports; a Reviewer (tax agent) approves the client's legal segment, the value mappings, exceptions and the report. The firm then tells its client what to fix and which deadline applies, and records which ASP the client appointed. See [PRD.md section 3](PRD.md#3-problem-buyer-users).

The repository exists to answer one question: will the firm pay after accounting for what its ASP already includes, and is there a monthly job after onboarding? Keep [Decision.md section 5.3](Decision.md#53-the-recurring-job-after-onboarding-p) and the stop rule in view before proposing any feature.

## Highest-consequence error

**False Ready** — a client entity is shown or reported as data-ready, or with a later deadline than the law gives it, when it is not.

Ways it happens: wrong Revenue band; wrong column mapped; a result kept after a rule pack, calendar, segment or mapping changed; an accepted exception counted as a pass; a mandatory field marked "not in this file" so that its rule never ran; a missing dataset read as "no findings"; staleness left to a background job; a date computed in the wrong time zone.

## Sensitive data

Client invoice exports: customer names and addresses, TRNs and TINs, prices, volumes, sometimes individuals' details. Firm credentials and TOTP secrets. Approved reports that clients rely on. Rule packs and calendars, whose integrity decides every status.

## Prohibited shortcuts

- Do not hard-code a deadline or a rule. Dates come from a calendar version; rules from a rule pack; both carry sources.
- Do not show one deadline for all clients. A segment that is not confirmed shows "Segment not confirmed".
- Do not treat an exception, a waiver, "not checked", "manual review" or "out of scope" as a pass, and do not skip the other checks on that record.
- Do not let a model, a heuristic or a default decide segment, deadline, arithmetic, status or access.
- Do not require a value the user does not have. Accept "unknown" and show its consequence.
- Do not use the words "compliant", "validated by" or a bare "ready". The only positive status is "Data-ready" with its pack version.
- Do not email a sign-in link as authentication; do not log cell values.
- Do not query the database outside the tenancy session, in the API or the worker.
- Do not store a stale flag or let a job decide staleness; derive it on read.
- Do not accept a client file, or send a message, before the Phase 0 gates (T-0.1.2, T-0.1.5) are passed.
- Do not add connectors, XML output or ASP-specific formats without the evidence in [PRD.md section 2](PRD.md#2-goals-and-non-goals).
- Do not change one economic number in Decision.md without re-running the rest.

## First verification checks when implementation begins

Definitions in [execution-plan.md section 8](execution-plan.md#8-tests).

1. UT-10 and UT-16: segment function and calendar give 30 October 2026 and 1 January 2027 for SEG-L, 31 March 2027 and 1 July 2027 for SEG-S, 31 March 2027 and 1 October 2027 for SEG-G, and, for a Person of unknown Revenue, both outcomes with 30 October 2026 governing the sort.
2. UT-11, UT-14 and UT-17: the status function never returns Data-ready with an accepted exception, an unchecked mandatory field, an unapproved mapping, a missing dataset, an unconfirmed segment, stale versions or data older than 45 days; an exception does not stop other checks.
3. IT-01: cross-firm access returns 404 with zero rows through API, files and worker.
4. IT-07 and IT-17: approval fails with 409 when any pinned version changed, and Stale is shown even when the notice job is dead.
5. UT-13: days remaining are computed in Asia/Dubai.
6. UT-09 and UT-12: decimal arithmetic and identical results on a repeat run.
7. OPS-04: one proposed start command brings up every service or fails by name.
