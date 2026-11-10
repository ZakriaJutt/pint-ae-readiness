# Design brief — PINT AE Readiness Desk

Screens: [App-flow.md](App-flow.md). Status vocabulary: [PRD.md section 5](PRD.md#5-status-vocabulary). All proposals **[P]**. WCAG references are to WCAG 2.2 [S: SRC-23]; nothing has been tested, so no conformance is claimed.

## 1. Principles and decisions

| ID | Decision |
|---|---|
| DD-01 | Tables first. The dashboard and fix list are dense, sortable tables on desktop; this is a working tool for accountants, not a marketing page |
| DD-02 | A status is always a word plus an icon plus a colour, in that order of reliance. Colour never carries meaning alone |
| DD-03 | Every date shows its segment and source on demand: a "Why this date" disclosure beside each deadline |
| DD-04 | Evidence beside the claim: a finding always shows file, sheet, row, column and the value found |
| DD-05 | Draft and approved are visibly different objects: watermark, border and label for drafts; a seal line with approver, date and versions for approved |
| DD-06 | The words "compliant" and "ready" on their own never appear. The only positive status is "Data-ready", always followed by the pack version |
| DD-07 | Suggestions look like suggestions: dashed outline and "Suggested" tag until a person confirms |
| DD-08 | The disclaimer "Not an Accredited Service Provider. This is not an ASP validation result." is part of the report template and the application footer |

## 2. Visual system

- **Layout:** left navigation (Clients, Monthly cycle, Rules, Settings) 220 px; content up to 1,440 px; client pages carry a sticky header with name, status and next step.
- **Typography:** one sans-serif family with tabular numerals for all numbers and identifiers; 16 px body, 14 px table text, 20 and 28 px headings; TRNs and codes in a monospaced face.
- **Colour:** neutral greys for structure; one blue for actions. Status hues: slate (Not started, Data incomplete), amber (Segment not confirmed, Review pending, Stale), red (Gaps open), red-outline (Checks incomplete), violet (Exceptions open), green (Data-ready). Text and its background meet 4.5:1; status chips and focus rings meet 3:1 against adjacent colours.
- **Components:** data table with sticky header, column sort buttons, row selection and a count line; status chip; deadline cell (date, days remaining, source disclosure); file drop zone with an equivalent button; mapping row (target field, source select, samples); finding drawer; version badge; confirm dialog; toast region; progress panel.
- **Hierarchy on any client page:** status and reason first, next step second, evidence third, history last.

## 3. Principal screens, enough to sketch

**S-04 Dashboard.** Top: four count tiles (past appoint-by without ASP; Gaps open; Stale; Data-ready) that act as filters. Below: filter bar, then the table with columns Client, Segment, Appoint by, Implement by, Days left, Data status, Score, Blockers, ASP status, Last run. Rows past a deadline carry a red left edge and the text "passed". A Stale banner sits above the table with "Re-run 6 stale clients".

**S-06 Segment.** Two columns. Left: the form in legal order (entity type, newly established, consumer-only, Revenue band, period end, evidence). Right: a result card that updates as the form changes: "Segment SEG-S. Appoint an ASP by 31 March 2027. Implement by 1 July 2027. Calendar CAL-2." with the quoted definition of Revenue beneath. For "unknown" the card reads "Segment not confirmed" and lists both outcomes with their dates, the earlier one first and marked "used for sorting until confirmed". The approval bar at the bottom is visible only to Reviewer and Owner.

**S-08 Mapping.** A table of target fields grouped by Seller, Buyer, Document, Line. Each row: field name with its rule reference, a select of source columns, five sample values, and a consequence note when unmapped or marked absent ("RC-14 cannot run. Unit checks will be reported as not checked, and this client cannot become Data-ready until the field is supplied."). A Reviewer bar at the bottom carries Approve mapping and Return. Value tables open in tabs below: Units, Emirates, Tax treatment, Document type, Buyer class.

**S-10 Fix list.** Left: grouped list by rule with counts. Centre: findings table (Record, Field, Value found, Expected, State). Right drawer on selection: plain description, source location with a "copy cell reference" control, the rule's source reference, history, and actions. Exceptions sit in their own tab with a count that never disappears.

**S-12 Report.** A paginated preview at print size. Page 1: firm logo, client name, status, score, segment and both dates, pack and calendar versions, check date. Page 2: blockers by rule. Page 3: exceptions with reasons and approver. Last page: method, limits and the disclaimer. The approval panel lists the five things the Reviewer is confirming.

## 4. Responsive behaviour

Desktop at 1,280 px and above is the design target. From 768 to 1,279 px the navigation narrows to icons with their text labels underneath (labels are always visible), and tables keep Client, Days left, Data status and ASP status, moving the rest into an expandable row. Below 768 px, which includes a desktop browser zoomed to 400%, every screen works in a single column: the upload screen uses the file button, and each mapping field becomes a stacked card with its select and samples. No task is withheld at any width. Content reflows without two-dimensional scrolling at 320 CSS px except inside data tables and the read-only source grid, which scroll in their own labelled, keyboard-focusable regions.

## 5. Interaction feedback and microcopy

- **Pending operation:** "Checking 12,480 invoice lines against rule pack RP-1. You can leave this page; the result will be here when you come back."
- **Recoverable error:** "We could not read sheet 'Sales Q3': the header row is empty. Choose the row that contains the column names, or upload a different file. Your other two files were accepted."
- **Human approval:** "You are approving this report for Al Noor Trading LLC. Status: Exceptions open (2). Segment SEG-S, approved by you on 3 February 2027. Rule pack RP-1, calendar CAL-2. This report does not say the client is Data-ready. Approve report".
- **Stale:** "Rule pack RP-2 was published on 12 March 2027. These results used RP-1. Re-run to see the current status."
- **Unknown accepted:** "Not known yet. You can continue. Until a Reviewer approves a Revenue band this client shows as 'Segment not confirmed' and is sorted by the earlier possible date, 30 October 2026."
- **Not checked:** "Buyer TRN was marked 'not in this file'. RC-07 could not be checked for 212 customers. This counts as an open blocker."
- **Exception:** "Accepting this exception keeps the finding visible and keeps the client out of Data-ready."

## 6. Evidence, correction, draft versus approved

- **Inspecting evidence:** every finding links to the stored row as uploaded (read-only grid with the cell highlighted) and to the rule's source reference in S-14. Every deadline links to its calendar row.
- **Correcting a suggestion:** in S-08 the user changes the select; the tag changes from "Suggested" to "Set by {name}"; nothing is applied until Confirm. A wrong confirmed mapping is corrected by a new version, never by editing results.
- **Correcting data:** at source, then re-upload. The product does not edit client data in place; the fix list says what to change and where.
- **Draft versus approved:** DD-05. Superseded reports keep their seal and gain a red "Superseded on {date} by {reason}" band.

## 7. Accessibility map

| Criterion (level) | Screens | Manual check |
|---|---|---|
| 1.3.1 Info and Relationships (A) | S-04, S-08, S-10 | Tables expose headers and sort state; mapping rows are labelled by field name; verify with a screen reader |
| 1.4.1 Use of Color (A) | S-04, S-10, S-12 | View in greyscale; every status still distinguishable by word and icon |
| 1.4.3 Contrast (Minimum) (AA), 1.4.11 Non-text Contrast (AA) | All | Measure chip text, chip borders, focus ring, red left edge |
| 1.4.10 Reflow (AA) | S-04, S-05, S-07, S-08, S-10, S-12 | 320 CSS px and 400% zoom at 1,280 px; upload and a full mapping can be completed; only table regions scroll horizontally |
| 2.1.1 Keyboard (A) | S-07, S-08, S-10 | Upload by button without drag; change a mapping; open and close the finding drawer; select rows and run a batch action, all by keyboard |
| 2.4.3 Focus Order (A), 2.4.7 Focus Visible (AA), 2.4.11 Focus Not Obscured (Minimum) (AA) | S-10 drawer, dialogs, sticky headers | Focus moves into the drawer and returns to the originating row; sticky header never fully hides the focused row |
| 2.2.1 Timing Adjustable (A) | Session expiry | Warning 2 minutes before the inactivity limit with "Stay signed in" |
| 2.5.8 Target Size (Minimum) (AA) | Table row actions, chips used as filters | At least 24 by 24 CSS px |
| 3.3.1 Error Identification (A), 3.3.3 Error Suggestion (AA) | S-01, S-06, S-07, S-08 | Submit invalid input; focus lands on the first error; the message names the field and the fix |
| 3.3.4 Error Prevention (Legal, Financial, Data) (AA) | S-06, S-10, S-12, S-16 | Approvals and deletion show a review step and can be checked before submission |
| 3.3.7 Redundant Entry (A) | S-05 to S-06, S-11 | TRN, licence and ASP name entered once and reused |
| 3.3.8 Accessible Authentication (Minimum) (AA) | S-01, S-02, S-18 | Password managers and paste work for password, TOTP code and recovery code |
| 4.1.3 Status Messages (AA) | S-07, S-09, S-04 batch | "Upload accepted", "Run finished: 14 blockers", per-item batch results announced without moving focus |

Each row is exercised by a test: A11Y-01 (2.1.1, 2.4.3, 2.4.7, 2.4.11), A11Y-02 (4.1.3, 1.3.1), A11Y-03 (1.4.1, 1.4.3, 1.4.11), A11Y-04 (1.4.10, 2.5.8), A11Y-05 (3.3.1, 3.3.3, 3.3.4, 3.3.7), A11Y-06 (2.2.1), A11Y-07 (3.3.8).

Known gap: no Arabic interface and no right-to-left layout in the MVP.

## 8. Vocabulary

Client entity; segment; appoint by; implement by; rule pack; calendar version; blocker; warning; exception; Data-ready; Stale; superseded; handoff pack; monthly cycle. Icons always carry a text label. "Upload" means a file from the firm; "export" means a file from the product.
