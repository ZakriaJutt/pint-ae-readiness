# Decision — PINT AE Readiness Desk

**Question this repository exists to answer:** will a UAE tax practice pay for cross-client invoice readiness work after accounting for what its Accredited Service Provider (ASP) already includes? Rules are versioned by effective date and client segment. The recurring job after initial onboarding must be defined.

Status: planning only. No customer has been interviewed, no message has been sent, no application exists. Willingness to pay is unproven.

## 0. Labels

| Label | Meaning |
|---|---|
| **[C]** | Stated in the owner's earlier discussion or its research record (the decision brief). The brief's unit-economics inputs are model assumptions even when labelled [C]; they are marked **[C-model]**. |
| **[S: SRC-nn]** | Read by the author on 2026-11-10 at the source listed in [section 13](#13-sources-and-assumptions). |
| **[A]** | Assumption. Never a finding. |
| **[P]** | Proposal by the author; needs the founder's decision. |

Results computed from assumptions are assumptions. Money is AED unless a line says otherwise. **Exchange rates:** 1 USD = 3.6725 AED (the dirham peg as given in the brief **[C]**; the Central Bank page returned HTTP 403, so the author did not re-read it) and 1 USD = 1.38 CAD (**scenario assumption [C-model]**, no sourced rate, no rate date). Direction used: CAD→AED = 3.6725 ÷ 1.38 = 2.66123; AED→CAD = 1.38 ÷ 3.6725 = 0.37577 (unrounded in every calculation). Scenario date: 2026-11-10. Every CAD figure below is a scenario conversion, not a quote.

## 1. Proposed decision

**Test, do not build yet [C: verdict "test"], and only if the first message can go out by Monday 11 January 2027.** Two gates now precede any outreach: written legal answers (LQ-1 to LQ-5) and the UAE-region file store. Preparation starts 16 November 2026; the earliest realistic first send is **Monday 14 December 2026 [A]**, four weeks later than the chat's plan assumed. Then: eight weekly cohorts with hand-delivered free checks; the 60-day pilot at AED 1,500; decision on **day 77 after the first send (28 February 2027 if sends start 14 December)**, not on the chat's 31 January. Build only the internal rule workbook until the first pilot is paid.

**Said plainly: the re-dated plan leaves little of the demand window.** The trigger is the 31 March 2027 appointment date. With a first send on 14 December the first pilots are paid about 19 January, only the first two weekly cohorts (expected 1.26 pilots) can finish 60 days before 31 March, the stop decision falls 31 days before that date, and the month-3 payment that answers the decisive question arrives from 20 March onward, mostly after it. What can still be tested in time is whether firms pay AED 1,500 before the deadline; whether they keep paying is learned after it. If the gates push the first send past 11 January 2027, day 77 passes 28 March and the test should not start in this form (section 9).

Three findings from primary sources shape the test:

1. **The gap is real but narrower than the brief states.** MoF assigns the pre-onboarding gap analysis and data extraction to the taxpayer, not the ASP [S: SRC-02 App. 1 step 1c, App. 2]. Zoho ties e-invoicing to a Zoho Books organisation [S: SRC-17]. Wafeq serves its own ledger and also says its ASP "connects your existing ERP, e-commerce platform or custom software to UAE e-invoicing through an API" [S: SRC-14], so a client need not move its books to use Wafeq. Neither page describes a check of a client's data before it contracts, a route for books kept in Excel, or one view across clients that use different ASPs. That remainder is the gap.
2. **The ASP's free floor is regulatory.** Every ASP must give each end user 100 free e-invoice exchange and reporting services a year, counted from the end-user agreement date [S: SRC-04 §3.2.5, citing MD 168 of 2026; the reviewer reports reading the same commitment in MD 168 itself, the author did not open it]. A small client's transaction charges may therefore be nil **[A]**; it still pays for a plan where the ASP requires one (Wafeq from AED 57, Zoho Professional AED 129 a month). A readiness fee is extra cost, not a substitute.
3. **No recurring job is evidenced.** Section 5.3 defines one as a proposal and section 7.4 shows the business as a one-off project. On the assumed funnel and the one verifiable prospect list, the product does not reach break-even in either case (section 7.5).

## 2. Market, people, current practice

| Item | Decision or record | Label |
|---|---|---|
| Launch market | Dubai and Sharjah bookkeeping and tax firms serving 30–150 SME clients on Excel, QuickBooks Online or Odoo | [C] |
| Buyer and budget owner | Managing partner or head of tax (FTA-registered tax agent); firm budget, "usually recharged to clients as a readiness fee" | [C] |
| Daily user | Accounting manager or senior bookkeeper who holds client exports (Preparer); a tax agent reviews (Reviewer) | [P] |
| Firm size | 3–40 staff | [C] |
| Current workaround | Readiness tracked in a spreadsheet; vendor checklists sent to clients; all clients pushed to one ASP (often Zoho or Wafeq) | [C] |
| Trigger | Clients under AED 50M must appoint an ASP by 31 March 2027 and implement by 1 July 2027 | [S: SRC-05 Art. 5(1)(b)] |
| Tax agents in the UAE | 936 (FTA board report, 30 April 2026); the FTA public directory lists 820 entries, listing label "last updated July 25, 2023" | [S: SRC-21], [S: SRC-09] |
| Modelled buyer benefit | 60 clients × 3 h × AED 120 = AED 21,600 of manual checking; at 1 h per client the saving is 60 × 2 × 120 = AED 14,400; recharge 60 × AED 500 = AED 30,000 | [C-model], every input an assumption |

**Vendor-advertised versus measured.** Everything in section 4 about competitors is vendor-advertised text. No measured customer outcome exists for any product in this market, including this one.

## 3. Rules by effective date and client segment

The product must never show one deadline for all clients. Segments and dates as read in the legal instruments:

| Segment | Definition | Appoint ASP by | Implement by | Source |
|---|---|---|---|---|
| SEG-L | Person, Revenue ≥ AED 50,000,000 | 30 October 2026 (passed) | 1 January 2027 | [S: SRC-06 Art. 1], replacing 31 July 2026 in [S: SRC-05 Art. 5(1)(a)] |
| SEG-S | Person, Revenue < AED 50,000,000 | 31 March 2027 | 1 July 2027 | [S: SRC-05 Art. 5(1)(b)] |
| SEG-G | Government Entity | 31 March 2027 | 1 October 2027 | [S: SRC-05 Art. 5(1)(c)] |
| SEG-N | Newly established Person in scope | Before its first invoice | Before its first invoice | [S: SRC-02 §8.4] (guideline text; legal article not located) |
| SEG-X | Person engaged exclusively in business-to-consumer transactions | Not subject until a Minister's decision | — | [S: SRC-05 Art. 5(2)] |
| SEG-U | Segment not confirmed (Revenue or entity type unknown) | Product state, not a legal class. Shows both outcomes; the earliest date the entity could legally have governs sorting and days-left | Same | [P] |

Two different things are versioned and have separate identifiers.

**Calendar versions** (the appointment and implementation dates per segment):

| ID | Instrument | What it sets | Source |
|---|---|---|---|
| CAL-1 | MD 244 of 2025 as issued | SEG-L appointment 31 July 2026; SEG-S and SEG-G as above | [S: SRC-05] |
| CAL-2 | MD 244 as amended by MD 66 of 2026 | SEG-L appointment 30 October 2026; PDF dated 14 May 2026; in force the day after publication (date blank on the document). Current version | [S: SRC-06] |

**Dated provisions** (they change which checks or dates apply inside a calendar version):

| ID | Provision | Dates | Source |
|---|---|---|---|
| PRV-1 | Pilot programme and voluntary implementation | From 1 July 2026; penalties apply only from a Person's mandatory date | [S: SRC-05 Art. 3–4], [S: SRC-02 §8.2] |
| PRV-2 | Intra-VAT-group transactions grace period | Invoices dated 1 January 2027 to 31 December 2028 (24 months) | [S: SRC-02 §6.3.2.1]; underlying decision not opened |
| PRV-3 | HSN codes | Optional now; mandatory date "to be announced" | [S: SRC-02 §12.2 item 28] |
| PRV-4 | All remaining Persons | After the phases complete, any Person in scope must appoint and implement | [S: SRC-05 Art. 5(1)(d)] |

A provision is stored with its own start and end dates and the rules it switches (schema.md `provisions`); a future amendment takes the next calendar number without colliding with a provision.

**Conflict recorded.** The MoF Guidelines V2.0 table prints "31st October 2026" for SEG-L [S: SRC-02 §8.3]; the amending decision says 30 October 2026 [S: SRC-06]; Zoho's page says 30 October [S: SRC-17]; the brief says 31 October [C]. **[P]** The product stores the legal instrument's date (30 October) and shows the guideline's date as a noted discrepancy. Both dates have passed; the conflict changes no pilot outcome but proves that the calendar needs a source and version on every row.

**Conflict recorded (2026-11-11, B1 review).** For Revenue of exactly AED 50,000,000 the sources disagree: the Guidelines table reads "Revenue ≥ AED 50,000,000" for SEG-L [S: SRC-02 §8.3]; the MoF announcement of MD 66 says revenues that "exceed AED 50 million" [S: SRC-24]. **[P]** The product never picks: a Revenue of exactly AED 50M is recorded as its own band, the entity shows as SEG-U (segment ambiguous) with both outcomes, the earlier SEG-L dates govern sorting and days-left, and a flag cites the two sources until the Reviewer has a ruling.

**Default and edge cases.** Revenue is "the gross income earned by a Person during the most recent Accounting Period, based on the financial statements" or, where none exist, "other documentation acceptable to the Authority" [S: SRC-05 Art. 1]. The instruments read do not say which reference date fixes "most recent" or what happens when a later period crosses the threshold. The product therefore records the accounting period end and the evidence type and lets Revenue be `unknown`. It never requires a number to proceed (PRD MH-02).

**One rule for an unconfirmed segment (SEG-U).** The row shows "Segment not confirmed" and both outcomes with their dates. For sorting, days-left and the overdue list it uses the earliest dates the entity could legally have: for a Person of unknown Revenue, SEG-L's 30 October 2026 and 1 January 2027, so the row sorts as overdue until a Reviewer confirms a band; for a government entity, SEG-G's dates whatever the Revenue. No Revenue figure is invented; the worst case is displayed as a possibility, labelled "if Revenue is AED 50M or more". SEG-N has no fixed date: the product stores "before first invoice", an optional first-invoice date, and sorts the row as overdue once that date has passed or if the client has already issued invoices.

**Validation rule packs.** Versioned by the specification release they implement:

| Pack | Basis | Released | Effective from | Source |
|---|---|---|---|---|
| RP-1 | PINT AE Billing 1.0.4 (Final) with MoF Mandatory Fields V1.1 (28 October 2026): 51 mandatory fields for a tax invoice, 49 for a commercial invoice | 2 June 2026 | Not published; **[A]** treated as the release date | [S: SRC-10, SRC-11, SRC-03] |
| RP-0 (history only) | PINT AE 1.0.0 (10 June 2025), 1.0.1 (31 July 2025), 1.0.2 (8 December 2025), 1.0.2-hotfix (28 January 2026), 1.0.3-hotfix (25 March 2026) | as dated | Not published | [S: SRC-11] |

Six releases in twelve months, none with a published effective date. The AE rule page lists 132 jurisdiction rules (44 ALIGNED, 88 IBR) [S: SRC-12]; RP-1 covers the mandatory fields at source-data level (PRD section 6), not all 132. A pass in this product is not a pass at an ASP.

## 4. What the ASP includes, and the gap

**What MoF states an ASP does** [S: SRC-02 §5.1, §5.2, §15.4, App. 4; SRC-04]:

| Stated ASP role | Stated as the taxpayer's job |
|---|---|
| Validate invoice data received from the supplier and convert it to the UAE XML | Calculating all invoice values |
| Onboard clients, explain requirements, work on integrations, enable testing | Gap analysis of data points; making the ERP able to extract them; data migration |
| Issue the participant identifier; exchange; report tax data to the FTA | Gathering each buyer's participant identifier |
| Use the latest specification; technical support; security; outage notices | Retaining records; reporting changes of circumstance via EmaraTax |
| Tell the client, event by event, that tax data reached the FTA | Monitoring errors and resolving them with the ASP |
| 100 free e-invoice exchanges per end user per year | Choosing and contracting the ASP |

**What Zoho and Wafeq publicly include** (vendor pages, read 2026-11-10):

| | Wafeq [S: SRC-14, SRC-15, SRC-16] | Zoho Books UAE [S: SRC-17, SRC-18] |
|---|---|---|
| Accreditation | Accredited, no. 129932; on the MoF list as entry 82 [S: SRC-07] | Accredited; on the MoF list as entry 86, no. 121988 [S: SRC-07] |
| E-invoicing price | Wafeq ledger users: "included in your Wafeq plan, with no separate ASP to buy". API route for other systems: no price on the page | Add-on for Professional and above: first 100 transactions free, then one-time packs from AED 41 per 100 |
| Ledger price, monthly billing, per organisation | Starter 57, Plus 80, Premium 200 (struck-through 69, 99, 249 also shown) | Standard 69, Professional 129, Premium 159, Elite 349, Ultimate 799 |
| Validation | Validates each invoice, converts, sends, reports; shows the rejection reason for correction | "create, validate, exchange, and manage" e-invoices |
| Clients not on the vendor's ledger | "Wafeq E-Invoicing ASP connects your existing ERP, e-commerce platform or custom software to UAE e-invoicing through an API". No systems named (QuickBooks, Odoo and Excel do not appear); no sandbox or pre-go-live validation described for API users | Not described; every description ties e-invoicing to a Zoho Books organisation |
| Readiness check before contracting | None described; an in-app prompt says when to switch e-invoicing on | None described |
| Multi-client view for firms | "One dashboard for every client"; partner commissions and tiers; free Premium account for the firm's own books; account manager | The page promotes Zoho Practice ("practice management software for ... accounting and bookkeeping firms") and an Accountant Program; neither page was read (the accountants page returned 404), so what they show per client is unverified |

**Like-for-like price per client entity per month, monthly billing, AED.** This product: Starter 299 ÷ 20 = 14.95; Pro 749 ÷ 75 = 9.99; Business 1,499 ÷ 250 = 6.00 at full plan limits [C], but 749 ÷ 30 = 24.97 for a 30-client firm on Pro. Wafeq Starter: 57 per client organisation including ledger and ASP. Zoho Professional: 129 per client organisation plus AED 0.41 per e-invoice above the free 100. The comparison is not substitutable: the client still needs an ASP after paying for this product. The brief's rule "per-client cost must stay well under AED 25" [C] is met only above about 40 enrolled clients on Pro (749 ÷ 40 = 18.73).

**Gap, stated honestly.** Three things no page read describes: a check of a client's data before the firm commits it to a provider; any route for a client whose books are in Excel, which cannot call an API; and one view across clients spread over several ASPs [C: "ASP-neutral"]. For a client on QuickBooks or Odoo, Wafeq's API route means an ASP will accept and validate its invoices without a ledger migration, if someone builds the connection; the price and the test facilities for that route are unknown. The gap closes for any client the firm migrates to Wafeq or Zoho, connects by API, or whose ASP runs the same checks free in its own test phase (MoF step 3). The chat's warning that Zoho and Wafeq "give this away free" [C] is confirmed for validation at submission, on-ledger and, for Wafeq, by API; it is not confirmed for a pre-contract check, for Excel clients, or for a cross-ASP view.

**Other entrants.** Aicountant.tech (ADS Management): press item says readiness assessment and a single workspace for multiple client entities; no price; no ASP status stated [S: SRC-19]. It is the closest direct competitor [C]. Alaan: a free 12-question readiness questionnaire, not data validation [S: SRC-20]. ADEPTS free readiness tool: page returned 403, status stays **secondary** [C]. RSM, ClearTax, Cygnet: not opened; brief's descriptions unverified.

## 5. Offer, pilot and the recurring job

### 5.1 Offer as stated in the chat

> Offer (owner's chat, translated): a free check of 3 client files, then a 60-day pilot at AED 1,500. [C]

Research record: 60 days, up to 30 client entities, AED 1,500 paid upfront, "credited to the first year if they continue" [C]. Channel: cold email and LinkedIn to registered tax agents with the free 3-file check; backup channel: co-marketing webinars with one mid-tier ASP [C]. Sales cycle 30 days [C-model].

### 5.2 Pilot terms [P]

| Term | Proposal |
|---|---|
| What AED 1,500 buys | For up to 30 client entities over 60 days: a gap report per entity within 2 UAE business days of its intake slot or its complete upload, whichever is later; one re-check per entity; the cross-client status sheet weekly; a handoff pack for each entity once its customer and item data have no open blocker; two review calls (day 30, day 45) |
| When paid | In full before day 1, by bank transfer or card against an invoice |
| Who signs, who pays | Managing partner signs; the firm pays; clients are not parties |
| Who supplies data | The firm's Preparer supplies three exports per entity (customers, items, last 3 months of sales invoices with lines) and confirms in the agreement that the firm is authorised by each client to share them |
| Sample inputs for the free check | The same three exports for 3 entities, anonymised if the firm prefers |
| Meaning of "credited to the first year" | The fee is the fee for months 1 and 2 (2 × 749 = 1,498 at Pro list). Nothing more is charged for those months and nothing more is discounted. The other reading, a further AED 1,500 off after the pilot, costs AED 1,500 per continuing account and is **not** assumed |
| Intake slots | The agreement carries a slot schedule. One founder can check 10 entities per 2-business-day window **[A]** (15 h at 1.5 h each); with n pilots running, each gets 10 ÷ n slots per window, so 30 entities take about 6, 12 or 18 business days for 1, 2 or 3 concurrent pilots |
| UAE business day | Monday to Friday, excluding the UAE federal public holidays listed by date in the agreement (list not sourced by the author); a day ends at 18:00 Asia/Dubai |
| Refund criterion | Full refund if fewer than 80% of entities whose complete files arrived by day 30 received a gap report within 2 UAE business days of the later of slot and complete upload. Both timestamps come from the delivery log shared with the firm. Dissatisfaction alone is not a refund ground. On the application the firm runs the check itself, so the criterion becomes: 80% of complete uploads reach a finished run within 1 hour and every support question is answered within 2 UAE business days |
| Pilot to recurring | Day 45 review; day 55 invoice for month 3 at the plan for the enrolled count (≤ 20: 299; 21–75: 749; 76–250: 1,499); payment by day 60 is the conversion. Monthly, cancel any time [C] |
| Delivery before software exists | The founder runs the checks by hand: the rule workbook (execution-plan T-0.1.3) applied to the three exports, a spreadsheet fix list, a PDF report; a second person checks the segment and dates of every entity and re-performs 5 entities per pilot before release (T-0.3.4). No client file is accepted before the storage and handling procedure exists and legal question LQ-4 is answered (T-0.1.5). Effort **[A]**: 1.5 h per entity, 45 h per 30-entity pilot, plus 4.5 h of the second person; at most 3 concurrent pilots |

### 5.3 The recurring job after onboarding [P]

**Evidence that recurring work exists** (not that anyone will pay for it): MoF's "Ongoing: manage changes" step [S: SRC-02 §13.5]; newly established clients must be onboarded before their first invoice [S: SRC-02 §8.4]; six specification releases in twelve months [S: SRC-11]; HSN codes to become mandatory at an unannounced date (PRV-3); the intra-group grace period ends 31 December 2028 (PRV-2); ASPs surface rejections per client inside their own applications [S: SRC-14].

**The monthly cycle, as proposed.** Per enrolled client entity, each month:

1. Delta check: customers and items created or changed since the last cycle, run against the current rule pack before they appear on an invoice.
2. Rule-pack and calendar watch: when a new PINT AE release or MoF document version is published, re-run stored data and list entities whose status changed.
3. Rejection log: rejected or failed invoices, entered by hand or imported from whatever the client's ASP lets it export, grouped by cause across clients.
4. New-entity intake: any client added by the firm starts at segment classification.
5. One monthly summary to the partner: entities at risk, days to each deadline, exceptions still open.

**What is not evidenced.** No firm has said it does, wants or would pay for steps 1–5. No ASP export format for rejections has been seen. After 1 July 2027 the client's own ASP validates every invoice in real time, which may leave only step 3 with any value. **The monthly fee is therefore unproven**; the brief itself says "revenue may be project-like" and churn "high after go-live" [C]. Section 7.4 carries the one-off case.

## 6. One paying account, one billable unit [P]

- **One paying account** = one firm (one legal entity, one workspace) inside a paid term: the 60 pilot days or a paid subscription month. An account starts when the pilot fee is received.
- **One billable unit** = one enrolled client entity (one legal person with its own TIN) in a calendar month, counted against the plan limit; AED 25 per entity above the limit [C].

| Price | AED per month | CAD (scenario) | Label |
|---|---|---|---|
| Starter, 20 entities | 299 | 112.35 | [C] |
| Pro, 75 entities | 749 | 281.45 | [C] |
| Business, 250 entities | 1,499 | 563.27 | [C] |
| Pilot, 30 entities, 60 days | 1,500 once = 750 per month | 563.65 once | [C] |
| Assumed revenue per account (ARPU) | 650 | 244.25 | [C-model] |

**Reconciliation.** 650 = 0.22 × 299 + 0.78 × 749: a mix of 22% Starter, 78% Pro, no Business, monthly billing, no overage, no annual discount **[A]**. This mix sits badly with the 30–150-client buyer, who fits Pro or Business; it holds only if about one account in five enrols 20 or fewer off-ledger clients. An ICP-consistent mix of 80% Pro and 20% Business would give 899; the lower 650 is kept. The brief's CAD list prices (99, 249, 499) are placeholders [C] and do not equal the conversions above. Usage: the AI line assumes about 60 file mappings a month [C-model], which matches roughly 60 entities each uploading one delta file in the monthly cycle; onboarding months need 3 files per entity.

## 7. Unit economics

### 7.1 Cost categories

| Category | Amount (AED) | Label |
|---|---|---|
| Startup, once | 4,500: the brief's 30-day cash budget of 9,000 ("about CAD 3,400"; 9,000 × 0.37577 = CAD 3,381.89) less the 4,500 sales budget; the brief does not itemise the split and names only a "legal review of 'not an ASP' wording". Plus **10,000 [A]** for the five written legal answers (CAD 3,757.66): a placeholder, no quote obtained, true cost unknown. Total 14,500 (CAD 5,448.60). The virtual desktop of T-0.1.5 is inside the hosting line of fixed cost | [C] total, [A] split and legal |
| Build effort | Brief: 140 h / 18 days, valued by the site model at CAD 100 an hour = CAD 14,000 = AED 37,257.25 [C-model]. This plan's own estimate: 412–644 h (execution-plan section 6) = CAD 41,200–64,400 = **AED 109,642.75–171,383.33** at the same rate **[A]**. It is cash if developers are paid and 2.9–4.6 founder-months if the founder builds; section 7.6 | [C-model], [A] |
| Fixed, monthly, excluding founder | 3,200 (CAD 1,202.45). The brief gives no composition. Bottom-up **[A]**: hosting, database, storage, backups and the pilot file store about 551; email and monitoring about 150; the remaining 2,499 is unallocated (legal, accounting, insurance, software). Sales tools are **not** in it; they are in the acquisition line | [C-model] |
| Founder compensation, monthly | CAD 6,000 = AED 15,967.39 | [C] |
| Variable, per account-month | 92.85 (section 7.2) | [C-model] |
| Initial acquisition | 1,800 per paying account (section 7.3) | [C-model] |
| Churn replacement | 6% × 1,800 = 108 per account-month to hold the base | [C-model] |

### 7.2 Gross profit per account-month

AI 6 + API 0 + hosting 12 + storage 3 + messaging 2 + support 45 + other 5 = 73.00. Payment 2.9% × 650 + 1.00 = 19.85. Direct cost 92.85. **Gross profit 650 − 92.85 = 557.15 (85.7%)**, CAD 209.36. The chat's "margin 86%" [C] reproduces.

### 7.3 Acquisition cost, payback, break-even

**One definition, used everywhere:** cash outreach spend ÷ paying accounts won (pilot fee received). Founder time is excluded because it is counted once, in founder compensation. 30-day sales budget 4,500 [C] ÷ 2.52 accounts = 1,785.71; the model's 1,800 is used, so the ramp spends 2.52 × 1,800 = 4,536 per batch, AED 36 more than the brief's budget, from that rounding alone. Loaded with founder time, for information only: the brief gives 80 founder hours per 30 days [C], but its own offer needs more. Per 400 firms: list and sending 20 h, replies 10 h, 12.6 calls at 1 h, 12.6 free checks of 3 entities at 1.5 h each = 56.7 h, proposals and admin 12 h: **111.3 h [A]**. At 15,967.39 ÷ 160 h = 99.80 an hour **[A]**, 111.3 h cost 11,107.32, and loaded acquisition cost = (4,500 + 11,107.32) ÷ 2.52 = **6,193.38**. (With the brief's 80 h it would be 4,953.85.) The brief's "about AED 900 per 100 prospects" would be 3,600 for 400 and leaves 900 for the other listed items; the two brief figures are not itemised against each other.

- Payback = 1,800 ÷ 557.15 = 3.23 months. Lifetime value = 557.15 ÷ 0.06 = 9,285.83.
- Contribution after churn replacement = 557.15 − 108 = 449.15.
- **Break-even without founder** = 3,200 ÷ 449.15 = 7.12 → **8 accounts**. Without replacing churn: 3,200 ÷ 557.15 = 5.74 → 6.
- **Break-even with founder** = (3,200 + 15,967.39) ÷ 449.15 = 42.67 → **43 accounts**. Without replacing churn: 34.40 → 35.

The chat's "Break-even 8 (43)" [C] reproduces.

### 7.4 Downside case: a one-off project

Same funnel and acquisition cost; the only change is that no account pays after the pilot.

- Revenue per account: 1,500, once.
- Direct cost: 2 × 73.00 + (2.9% × 1,500 + 1.00 = 44.50) = 190.50. Gross profit 1,309.50.
- After acquisition: 1,309.50 − 1,800 = **−490.50 per account** before any fixed cost.
- Price that covers direct and acquisition cost only: (1,800 + 146 + 1) ÷ 0.971 = 2,005.15.
- Price that also covers eight months of fixed cost (16 November 2026 to mid-July 2027) across the 5.04 accounts of section 7.5: (8 × 3,200 ÷ 5.04 + 1,947) ÷ 0.971 = 7,236.22, or 241.21 per entity for 30 entities; with founder compensation 33,338.24, or 1,111.27 per entity.

Against the modelled recharge of AED 500 per client [C-model], a project price near AED 7,200 for 30 clients leaves the firm 30 × 500 − 7,236 = 7,764. **[P]** If month-3 conversions fail, test project pricing before stopping. At the pilot price, the one-off business loses money on every account.

### 7.5 Cash during the ramp

Timeline: preparation month 0 runs 16 November to 13 December 2026 and carries one month of fixed cost and the legal answers; the first send is Monday 14 December 2026 **[A]**, which depends on the lawyer answering by 11 December and on T-0.1.5; months are 30-day blocks from the first send (month 2 starts 13 January 2027, month 3 on 12 February, month 5 on 13 April). Every week the gates slip adds 800 of fixed cost and 3,991.85 of founder compensation and moves every later date by a week. Pilots are delivered by hand, so revenue does not wait for the application. Rules: 400 first touches a month in months 1 and 2, then none, because the only countable list is exhausted (section 8); each batch yields 2.52 accounts a month later; acquisition spend 2.52 × 1,800 = 4,536 in the outreach month; pilot fee received at pilot start; pilot months cost 73 per account plus the 44.50 payment fee; from account-month 3, ARPU 650 at 92.85 direct cost, churn 6% a month from the second subscription month; startup 4,500 in month 1; pilot-to-subscription continuation 100% **[A]** in the base case, the brief's implicit assumption.

**Base case (AED)**

| Month | First touches | New accounts | In pilot | Subscribed | Revenue | Direct cost | Fixed | Acquisition | Startup | Net without founder | Cumulative without founder | Cumulative with founder |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 3,200 | 0.00 | 10,000 | −13,200.00 | −13,200.00 | −29,167.39 |
| 1 | 400 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 3,200 | 4,536.00 | 4,500 | −12,236.00 | −25,436.00 | −57,370.78 |
| 2 | 400 | 2.52 | 2.52 | 0.00 | 3,780.00 | 296.10 | 3,200 | 4,536.00 | 0 | −4,252.10 | −29,688.10 | −77,590.27 |
| 3 | 0 | 2.52 | 5.04 | 0.00 | 3,780.00 | 480.06 | 3,200 | 0.00 | 0 | 99.94 | −29,588.16 | −93,457.73 |
| 4 | 0 | 0.00 | 2.52 | 2.52 | 1,638.00 | 417.94 | 3,200 | 0.00 | 0 | −1,979.94 | −31,568.10 | −111,405.06 |
| 5 | 0 | 0.00 | 0.00 | 4.89 | 3,177.72 | 453.93 | 3,200 | 0.00 | 0 | −476.21 | −32,044.31 | −127,848.65 |
| 6 | 0 | 0.00 | 0.00 | 4.60 | 2,987.06 | 426.69 | 3,200 | 0.00 | 0 | −639.63 | −32,683.94 | −144,455.68 |
| 7 | 0 | 0.00 | 0.00 | 4.32 | 2,807.83 | 401.09 | 3,200 | 0.00 | 0 | −793.25 | −33,477.19 | −161,216.33 |
| 8 | 0 | 0.00 | 0.00 | 4.06 | 2,639.36 | 377.02 | 3,200 | 0.00 | 0 | −937.66 | −34,414.85 | −178,121.38 |
| 9 | 0 | 0.00 | 0.00 | 3.82 | 2,481.00 | 354.40 | 3,200 | 0.00 | 0 | −1,073.40 | −35,488.25 | −195,162.17 |
| 10 | 0 | 0.00 | 0.00 | 3.59 | 2,332.14 | 333.14 | 3,200 | 0.00 | 0 | −1,201.00 | −36,689.25 | −212,330.55 |
| 11 | 0 | 0.00 | 0.00 | 3.37 | 2,192.21 | 313.15 | 3,200 | 0.00 | 0 | −1,320.94 | −38,010.19 | −229,618.88 |
| 12 | 0 | 0.00 | 0.00 | 3.17 | 2,060.68 | 294.36 | 3,200 | 0.00 | 0 | −1,433.68 | −39,443.87 | −247,019.95 |

Month 0 is the preparation month: fixed cost 3,200 and, in the Startup column, the 10,000 legal placeholder; with founder it also carries one month of compensation. Months 1 to 12 are unchanged per month from the first version of this table; every cumulative figure is lower by 13,200 without founder and 29,167.39 with founder. Subscribed accounts are shown to two decimals and computed unrounded. Net with founder = net without founder − 15,967.39.

- **There is no trough.** With 5.04 accounts at most and 6 needed even without replacing churn, monthly cash is negative from month 4 onward and the deficit grows. Month 12: AED −39,443.87 (CAD −14,821.66) without founder; AED −247,019.95 (CAD −92,821.66) with founder. Month 18: −50,061.84 and −353,442.27.
- **Downside (one-off, section 7.4):** identical through month 3, then no revenue. Month 4 −32,972.12, month 12 **−58,572.12** (CAD −22,009.40) without founder and **−266,148.21** (CAD −100,009.40) with founder; falling by 3,200 or 19,167.39 a month.
- **Sensitivities.** Continuation 50%: month 12 −49,007.99 without founder. The chat's single batch of 400: −47,344.01. Four batches (1,600 distinct firms, existence unknown): the deepest point is −37,156.20 in month 4, subscribed accounts peak at 9.21 in month 7, monthly cash is positive in months 5–14, then churn pulls the base back under 6; cumulative is still −26,433.12 at month 12 and never recovers the outlay within 18 months. With founder: −234,009.20 at month 12.

### 7.6 Build cost, delivery capacity and refunds

None of these three is in the brief's model or in the table above; each makes the picture worse.

- **Build.** On the "continue" branch only. Bought at CAD 100 an hour, 412–644 h add AED 109,642.75–171,383.33 between months 3 and 8. Month-12 cumulative cash then becomes **−149,086.62 to −210,827.20** without founder compensation (CAD −56,021.66 to −79,221.66) and −356,662.71 to −418,403.29 with it (CAD −134,021.66 to −157,221.66). If the founder builds instead, no cash moves but 2.9–4.6 months of full-time work are needed from someone who is already selling (111.3 h per batch) and delivering by hand (227 h for five pilots). Counted from the 28 February 2027 gate, one developer finishes between late May and mid-July 2027: at best a month before the 1 July go-live, at worst after it.
- **Delivery capacity.** Five pilots are 151 entities; at 10 entities per 2-business-day window that is about 30 business days of nothing else. Pilots 4 and 5 start later, which the slot schedule in section 5.2 makes explicit to the buyer. The second-person check (4.5 h per pilot) costs AED 1,197.55 per pilot at CAD 100 an hour if paid: 80% of the fee.
- **Refunds.** A refunded pilot returns 1,500 and keeps its 1,800 acquisition and 190.50 direct cost: a loss of 1,990.50, and no month-3 revenue. If 20% of pilots were refunded **[A]**, the base case loses 5.04 × 0.2 × 1,500 = 1,512 by month 3 and about a fifth of its later subscription revenue. The refund rate is unknown.

**Plainly:** on these assumptions the register-sized prospect pool cannot reach break-even without founder compensation, and 43 accounts with founder compensation would need 43 ÷ 0.0063 = 6,825 distinct firms contacted, more than seven times the 936 tax agents that exist. Reaching it needs a partner channel, as the brief says ("50–100 firms needs an ASP or Odoo partner channel") [C], or a much higher price per firm.

**Missing inputs:** distinct ICP firms; real reply, meeting and close rates; continuation after day 60; churn across 1 July 2027; tier mix; support hours per account; composition of the 3,200; refund rate; tax treatment of a fee invoiced from Canada to a UAE firm.

## 8. Funnel from distinct reachable prospects

Chat funnel [C]: "400 → 28 jawab → 12-13 demos → 2-3 customers". Recomputed with the brief's rates **[A]**: 400 × 7% = 28 replies; × 45% = 12.6 demos; × 20% = 2.52 paying accounts. Probability per contacted firm = 0.07 × 0.45 × 0.20 = 0.0063.

**Distinct reachable prospects.** The FTA "Registered Tax Agents" directory lists 820 entries, each an individual agent with firm name, emirate, email and telephone, filterable by emirate [S: SRC-09]. Several agents share a firm, so distinct firms are fewer than 820; the Dubai and Sharjah, 30–150-client subset is smaller again. **The count of distinct ICP firms is unknown.** The base case's 800 contacts and the chat's 400 both assume the directory and the Zoho, Wafeq, ICAI and ProAdvisor directories [C] together yield that many distinct firms after de-duplication. If the whole directory were distinct ICP firms, it would yield 820 × 0.0063 = 5.17 accounts.

## 9. Stop rule

**Owner's chat, translated [C]:** When to stop: fewer than 2 pilots by 31 January 2027. Zoho and Wafeq are giving this same thing away free; this is a big danger.

Research record [C]: "Stop if fewer than 2 paid pilots by 31 January 2027, or if firms say their ASP already gives them a free multi-client readiness view." Invalidation [C]: "10 of 12 interviewed firms say their chosen ASP already validates client data for free before onboarding." Roadmap gates [C]: at least 6 of 12 firms have no client-level readiness view; "AED 3,000 MRR or stop".

**Re-dating.** The chat fixed a calendar date on the assumption that outreach began at once. The legal gate and the file store now come first, so the count is tied to the first send, not to the calendar: **day 1 = first send; SR-1 is counted at the end of day 77.** With the first send on 14 December 2026 that is 28 February 2027; the single-pilot recount is day 91, 14 March 2027; SR-4 is day 44, 26 January 2027. Weekly cohorts of 100 close 30 days after the week ends, on days 37, 44, 51, 58, 65, 72 (19 January to 23 February); week 7 closes on day 79. So 600 contacts can have closed by day 77 whatever the start date, and the figures below hold. Two warnings: weeks 2 and 3 fall on the year-end holidays, when the assumed 7% reply rate is least plausible; and the latest first send that keeps day 77 before the 31 March 2027 appointment date is **Monday 11 January 2027** (day 77 = 28 March). Later than that, the gate decision comes after the deadline that creates the demand, and the test is abandoned or re-planned around the 1 July 2027 go-live.

**If the chat's date were kept instead.** With the first send on 14 December and the stop still on 31 January 2027, only weeks 1 and 2 (200 contacts) would have closed: P(fewer than 2) = **0.641**. For a first send one or two weeks after 16 November the figure would be 0.177 (500 closed) or 0.282 (400). A fixed 31 January date would stop the test mostly because of the gates.

**Consistency check, counted from the first send.** Expected pilots by day 77: 600 × 0.0063 = 3.78. With X ~ Binomial(600, 0.0063):

- P(X < 2) = 0.9937^600 + 600 × 0.0063 × 0.9937^599 = 0.0226 + 0.0858 = **0.108**. The rule stops a product that performs exactly as assumed about one time in nine.
- With only the chat's 400 contacts: 0.0798 + 0.2024 = **0.282**.
- If the true close rate were half the assumption, the rule would still pass with probability 0.564 at 600 contacts. It is a weak test of the rates.
- "AED 3,000 MRR" in week 4 cannot be met: no subscription month exists before day 61 of the first pilot.

**Revised rule [P]. This changes the chat's rule; it is not the chat's rule.**

| ID | Rule |
|---|---|
| SR-1 | At the end of day 77 after the first send (28 February 2027 for a 14 December start; Asia/Dubai), count paid pilots (signed agreement and AED 1,500 received). Two or more: continue. None: stop. Exactly one: continue only if two further firms have signed with payment due by day 91 (14 March 2027); recount then; fewer than 2: stop. If the first send has not happened by 11 January 2027, do not start. False-stop probability at day 77 with 600 closed contacts: 0.108 for the count alone; for the rule with its recount it is not computed (it needs a rate for "signed, payment due") and lies between 0.023 and 0.108 |
| SR-2 | Ask every discovery call: "For your clients that are not on your provider's own ledger, does that provider, or any ASP you use, already give you free (a) a check of the client's data before you commit it, including by API connection, and (b) a view across your clients?" Stop if 10 or more of the first 12 answers are yes to both [C threshold]; re-scope to Excel-kept clients only if 7–9 |
| SR-3 | If none of the first 3 pilots pays for month 3, the recurring job is not wanted: switch to project pricing (section 7.4) or stop |
| SR-4 | Channel: fewer than 14 replies from the first 400 by day 44 (26 January 2027; half the assumed 7%): move to the backup channel [C] |

## 10. Strongest evidence, strongest counterargument, what would change the decision

**Strongest evidence.** Dated legal deadlines per segment [S: SRC-05, SRC-06]; MoF places gap analysis and data extraction on the taxpayer [S: SRC-02]; neither Wafeq nor Zoho describes a check before contracting or a route for Excel-kept books [S: SRC-14, SRC-17]; 86 ASPs now compete for the same clients [S: SRC-07], so a firm has a real choice to manage.

**Strongest counterargument.** The ASP validates the same fields for free during its own onboarding test, the first 100 e-invoices a year are free by regulation, Wafeq gives firms a free Premium account and one dashboard, and 1 July 2027 ends the trigger. A firm can migrate every client to one ASP, or connect a client's existing system to Wafeq by API [S: SRC-14], and never need a neutral checker [C: failure mode]. The economics in 7.5 do not close even if firms do buy.

**Evidence that would change the decision.** Towards building: 2 paid pilots by the SR-1 date, SR-2 answers mostly "no", and at least 2 of the first 3 pilots paying month 3. Towards project pricing: pilots paid but SR-3 fails. Towards stopping: SR-1 or SR-2 fires, or a deadline extension is announced (it removes the trigger [C]). Towards a partner model: an ASP offers to pay for pre-cleaned clients [C].

## 11. Open decisions for the founder

1. Accept the revised stop rule (section 9) or keep the chat's wording.
2. Confirm the reading of "credited to the first year" (section 5.2).
3. Confirm paying account and billable unit (section 6) and the 22/78 tier mix behind ARPU 650.
4. Pilot data before the application exists: **[P]** resolved as a gate, not left open. Files are stored and worked only in the UAE-region store of T-0.1.5; no file is accepted until that task and legal question LQ-4 are done. The founder accessing that store from Canada is itself part of LQ-4.
5. Whether to replace the brief's email magic link with password plus TOTP (TRD AD-05).
6. Which entity invoices UAE firms, and its tax treatment (not decided in chat).
7. Whether to pay developers for the build (section 7.6) or wait for founder time.
8. Who the second checker of T-0.3.4 is.
9. Accept counting SR-1 from the first send (28 February 2027) instead of the chat's 31 January, and the 11 January 2027 last-start rule.
10. The budget for the legal answers (10,000 is a placeholder).

## 12. Go-to-market plan

Nothing here has been done. Rates are [A] unless labelled.

**Ideal customer profile.** Dubai or Sharjah bookkeeping or tax firm, 3–40 staff, 30–150 SME clients [C]; at least 20 clients under AED 50M, most not on Zoho or Wafeq, no single standard ASP [C: qualify]. Trigger: the 31 March 2027 appointment date, a client asking "which provider do we use", a first rejected invoice in the voluntary phase [C]. Disqualifiers: all clients already on one ASP ledger; fewer than 20 SEG-S clients; firm is itself an ASP or resells one exclusively; firm cannot share client data.

**Named roles.** Feels the pain: accounting manager who cleans TRNs and item data. Signs and pays: managing partner. Can block: the head of tax who already recommended an ASP, and any client that refuses data sharing. Supplies sample data: the accounting manager, with the partner's written confirmation of client authority.

**Prospect list.** Source 1: FTA Registered Tax Agents directory, 820 entries [S: SRC-09], filtered to Dubai and Sharjah, de-duplicated by firm name and email domain. Sources 2–4: Zoho and Wafeq partner directories, ICAI Dubai Chapter, QuickBooks ProAdvisor directory [C], counts unknown. Check: each row has firm, role holder, public email, emirate, and a note on client base; rows without a named partner are dropped. Distinct ICP firms: unknown until execution-plan T-0.1.1 is done.

**Legal gate before the first send.** The UAE rules that may govern this outreach were not read at any primary source (the federal legislation site returned 403): the personal data protection law (Federal Decree-Law 45 of 2021), the telecommunications regulator's rules on unsolicited electronic communications, Cabinet Resolutions 56 and 57 of 2024 on telemarketing, and the FTA website's terms of use. All are **unverified, no source consulted**; secondary summaries seen by the reviewer describe consent requirements for marketing messages and approval, do-not-call and time-window duties for marketing calls. No message is sent until a UAE-qualified lawyer answers in writing (execution-plan T-0.1.2):

| ID | Question |
|---|---|
| LQ-1 | May a vendor based in Canada send unsolicited business email to UAE tax agents at addresses published in the FTA directory, and under which instrument? Is prior consent or an opt-out required? |
| LQ-2 | Do Cabinet Resolutions 56 and 57 of 2024 apply to calls from a foreign vendor to UAE firms' landlines? What licence, do-not-call check and calling hours apply? |
| LQ-3 | Do the FTA site's terms allow its directory contact details to be used for marketing? How are LinkedIn connection messages treated? |
| LQ-4 | May client invoice data stored in the UAE, which can name individuals, be accessed by a person in Canada? What must the pilot agreement say, and what breach-notice duties exist? |
| LQ-5 | Is the "not an ASP" wording sufficient, and does offering readiness checks for a fee need any registration with the FTA or MoF? |

If LQ-1 is answered no, cold email is dropped, the funnel rates in section 8 no longer apply to any channel, and the test moves to LinkedIn (subject to LQ-3) and the backup channel [C]. The brief's cold-call script [C] is not used unless LQ-2 clears it.

**Channel and sequence.** Subject to the gate: cold email with LinkedIn connection [C]. Day 0 email; day 3 LinkedIn connection; day 7 follow-up; day 14 last note. Volume one founder can sustain: **100 new firms a week**, 400 in the first 30 days (the chat's funnel), a second 400 in days 31–58 if the list holds them.

**Message (synthetic; adapted from the brief's draft, never sent).**

> Subject: Which of Al Noor Accounting's clients miss 31 March?
>
> Hi Ms Rahman, clients under AED 50M must appoint an e-invoicing provider by 31 March 2027. I check a client's Excel, QuickBooks or Odoo exports against the PINT AE mandatory fields and return a fix list per client and one status sheet across clients. I am not an ASP and do not transmit invoices. May I run three of your client files free this week? I need a customer list, an item list and three months of sales invoices for each. If it is useful, the paid pilot is 60 days, up to 30 clients, AED 1,500.

> Follow-up, day 7: Ms Rahman, one question even if the timing is wrong: does the provider you recommend already check a client's data before onboarding, free? If yes, I will stop writing. If not, the three-file check stands.

**Pilot offer and conversion.** Section 5.2.

**Objections and honest answers.**

| Objection | Answer |
|---|---|
| "Our ASP will handle validation." [C] | It will, after the client is onboarded and testing, and free. This finds the gaps before you commit a client to a provider. For clients already on Wafeq or Zoho ledgers you do not need this |
| "You are not accredited." [C] | Correct. Nothing is transmitted. You get clean data and hand it to the ASP you choose |
| "After July 2027 we will not need it." [C] | Possibly true. The monthly plan can be cancelled at any time; a one-off project price is the alternative |

**Before day 1.** Preparation from 16 November 2026: list, workbook, fixtures, file store, agreement, and the legal questions sent in the first week. Cash before the first send: 3,200 fixed plus the 10,000 legal placeholder **[A]**. Founder hours: 58–90 (execution-plan M0.1).

**First 30, 60, 90 days** (day 1 = first send, 14 December 2026 **[A]**; day 30 = 12 January, day 60 = 11 February, day 90 = 13 March 2027; expected values, not targets met)

| | Day 30 | Day 60 | Day 90 |
|---|---|---|---|
| First touches, cumulative | 400 | 800 | 800 |
| Replies (7%) | 28 | 56 | 56 |
| Discovery calls with free check (45%) | 12.6 | 25.2 | 25.2 |
| Paid pilots (20%, 30 days after the cohort week) | 0 | 2.52 | 5.04 |
| Recurring paid accounts | 0 | 0 | 0 (first possible on day 97, 20 March 2027) |
| Cash spent on acquisition | 4,536 | 9,072 | 9,072 |
| Cash spent in total, without founder (section 7.5) | 25,436 | 29,688 | 29,588 |
| Founder hours, sales (111.3 per 400 firms [A]; the brief says 80 [C]) | 111 | 223 | 223 |
| Founder hours, hand delivery of pilots | 0 | about 60 | about 227 (5.04 × 45 h), plus about 23 h of the second checker |

The 111.3 hours per 400 firms are itemised in section 7.3. Sales and delivery together are about 450 founder hours in 90 days, against roughly 480 available at 160 a month, before any build work. Hand delivery of five pilots exceeds the 3-pilot capacity of section 5.2, which is why pilots 4 and 5 are scheduled later and execution-plan Phase 1 starts at the first paid pilot. These are the same 400 per month, 0.0063 and 1,800 used in sections 7.5 and 8, and give the same 5.04 accounts.

**GTM stop rule.** SR-1 to SR-4 in section 9.

## 13. Sources and assumptions

All consulted 2026-11-10. Jurisdiction UAE federal unless stated.

| ID | Source | Scope | Access |
|---|---|---|---|
| SRC-01 | MoF e-invoicing page, mof.gov.ae/en/about-us/initiatives/einvoicing/ (footer: updated 10/11/2026) | Model, document list, list of decisions | Open; timeline is an image, not read |
| SRC-02 | MoF, UAE Electronic Invoicing Guidelines V2.0, 26 October 2026, 58 pp., mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf | Scope, phases, ASP roles, scenarios, appendices | Full text read. The brief's URL (…/2026/06/…V-1.1-01June2026.pdf) returned the same file |
| SRC-03 | MoF, UAE Electronic Invoice Mandatory Fields V1.1, 28 October 2026 | 51 and 49 mandatory fields | Full text read |
| SRC-04 | MoF, Considerations for Selecting an ASP V1.1, 28 October 2026 | Selection criteria; 100 free e-invoices | Full text read |
| SRC-05 | Ministerial Decision 244 of 2025, PDF on tax.gov.ae | Phases, Revenue definition | Full text read; issue date blank |
| SRC-06 | Ministerial Decision 66 of 2026, PDF on mof.gov.ae (file dated 14 May 2026) | Amends Art. 5(1)(a) | Full text read; issue date blank |
| SRC-07 | MoF list of accredited service providers | 86 providers; Wafeq, Zoho entries | Open |
| SRC-08 | FTA e-invoicing page, tax.gov.ae/en/content/uae.einvoicing.aspx (updated 2 November 2026) | Still links Guidelines V1.1, a "pre-approved" provider list and Cabinet Decision 106 of 2025 | Open; older than SRC-01 |
| SRC-09 | FTA Registered Tax Agents directory, tax.gov.ae/en/tax.support/tax.agents/registered.tax.agents.aspx | 820 entries, fields, filters | Open; first 12 rows seen |
| SRC-10 | OpenPeppol, UAE specifications index, docs.peppol.eu/poac/ae/ | Billing, self-billing, tax data document all 1.0.4 | Open |
| SRC-11 | PINT AE Billing release notes | Releases and changed rules | Open |
| SRC-12 | PINT AE jurisdiction-aligned rules (invoice) | 132 rules, texts | Open; severities not shown |
| SRC-13 | PINT AE Billing BIS | Type codes, flags, tax categories, units, endpoints | Open |
| SRC-14 | wafeq.com/en-ae/asp-e-invoicing-uae (opened twice on 2026-11-10) | Inclusions; API route for existing ERP, e-commerce or custom software | Vendor page; the linked "Wafeq ASP solutions" page not read |
| SRC-15 | wafeq.com/en-ae/pricing | Plan prices | Vendor page; per-plan features behind a toggle, not read |
| SRC-16 | wafeq.com/en-ae/accountants | Firm programme | Vendor page |
| SRC-17 | zoho.com/ae/books/e-invoicing/ (opened twice) | Inclusions, dates quoted, links to Zoho Practice and the Accountant Program | Vendor page; linked pages not read |
| SRC-18 | zoho.com/ae/books/pricing/ | Plan and pack prices | Vendor page |
| SRC-19 | Khaleej Times network item on Aicountant.tech, 24 July 2026 | Launch claims | Sponsored-style content |
| SRC-20 | alaan.com e-invoicing readiness check | Questionnaire tool | Vendor page |
| SRC-21 | maktoum.ae, FTA board meeting, 30 April 2026 | 936 tax agents, 587,000 VAT and 743,000 corporate tax registrants | Open |
| SRC-22 | OWASP ASVS 5.0.0, chapters V3, V4, V5, V6, V7, V8, V13, V14, V16 (GitHub, tag v5.0.0) | Security requirements | Open |
| SRC-23 | W3C, WCAG 2.2 Recommendation | Success criteria | Open |
| SRC-24 | MoF news, "Ministry of Finance announces targeted amendments to e-invoicing system decisions", mof.gov.ae/en/news/ministry-of-finance-announces-targeted-amendments-to-einvoicing-system-decisions/ | MD 66 of 2026: SEG-L appointment moved to 30 October 2026 for revenues that "exceed AED 50 million" | Opened by the independent B1 reviewer on 2026-11-11, not by the author |

**Not opened or blocked:** Central Bank of the UAE peg page (403); MoF legislation index (404); Ministerial Decisions 243 of 2025, 168 and 197 of 2026 (the reviewer reports reading MD 168); the federal legislation site, uaelegislation.gov.ae (403), so Federal Decree-Law 45 of 2021 and Cabinet Resolutions 56 and 57 of 2024 were not read; the telecommunications regulator's unsolicited-communications rules; the FTA website terms; Wafeq's ASP solutions page; Zoho Practice and the Zoho Accountant Program; Cabinet Decision 173 of 2026 (penalties); ADEPTS release (403); Zoho accountants page (404); RSM, ClearTax, Cygnet; QuickBooks and Odoo API terms; the UAE personal data protection law. Every claim that depends on them is "unverified, no source consulted".

**Departures from the brief:** SEG-L appointment date is 30 October 2026 in the legal text, not 31 October; the guidelines file is V2.0 at both URLs; MoF now lists accredited, not pre-approved, providers; the 100 free transactions are a regulatory minimum, not a Zoho offer; the chat's "18 days" build is not adopted (execution-plan section 6); the brief's 80 founder hours per 30 days are replaced by 111.3; "handoff pack in the import format of 3 common ASPs" is reduced to a generic pack because no ASP import format was read.

**Brief items not adopted or not used, kept here so they are not lost [C]:** launch price AED 599, floor AED 199 and ceiling AED 2,499 (no tier or pilot uses them; 599 would lower ARPU below 650 if it replaced Pro); 15% annual discount (not modelled: the offer is monthly, cancel any time; Pro annual would be 636.65 a month); referral offer of one free month per referred firm that runs 10 checks, and an ASP referral fee (not in the plan until a first account exists); the cold-call script (held behind LQ-2); Abu Dhabi in the LinkedIn search (launch is Dubai and Sharjah); ICP range 20–300 clients in the research record against the chat's 30–150 (the chat's range is used); the roadmap's week-2 gate "2 pilots paid or 4 verbal commitments with dates" (replaced by SR-1; verbal commitments do not count); the brief's gap notes on ClearTax ("enterprise sales motion") and Cygnet ("sold as part of an enterprise ASP engagement"), both unverified.

**Assumptions preserved:** every [C-model] input in section 7; all funnel rates; 30-day sales cycle; 100% continuation in the base case; RP-1 effective date; the 14 December 2026 first send; the AED 10,000 legal placeholder; hand-delivery hours and slots; the 111.3 sales hours; the CAD 100 hourly build rate; the 22/78 tier mix.
