# Compliance self-check — PINT AE Readiness Desk

**This is not legal advice.** It is the owner's own research of primary sources, written down so that anyone can follow it. No lawyer reviewed it. On 2026-11-11 the owner decided that no lawyer will be hired for now and accepted the remaining risk (Decision.md section 11, item 13). Where a primary text could not be opened, this file says so and labels the secondary source used.

- Research date: 2026-11-11. Every source in section 12 was opened on that date unless marked otherwise.
- Quotes are short (under 15 words). Arabic quotes from the UAE data protection law are followed by an unofficial English translation by the author.
- `[P]` marks an owner decision or a design change that the owner must sign. Nothing here rewrites the product. Product facts stay in Decision.md, PRD.md and TRD.md.
- Risk levels: **low** = the rule is clear and we can follow it; **medium** = the rule is unclear or enforcement is unknown, and the steps below lower the risk without removing it; **high** = we cannot follow the rule in our current form.

| Section | Legal question (original text kept in Decision.md section 12) | Residual risk after the steps |
|---|---|---|
| 1 | LQ-1 Cold business email to UAE tax agents, sent from Canada (UAE spam policy, UAE data law, CASL) | Medium if we send; **low** under the partner model of section 8 |
| 2 | LQ-2 Marketing calls (Cabinet Resolutions 56 and 57 of 2024) | Low, because we make no calls |
| 3 | LQ-3 FTA directory contacts; LinkedIn messages | High for exporting the FTA directory (red line); medium for LinkedIn |
| 4 | LQ-4 Client invoice data in the UAE, accessed from Canada; agreement; breach notice | Medium |
| 5 | LQ-5 "Not an ASP" wording; any FTA or MoF registration | Low |
| 6 | Trade licence for a foreign company selling software remotely | Medium |
| 7 | VAT on the invoices we issue (reverse charge) | Low for VAT-registered firms; medium otherwise |

---

## 1. LQ-1: cold business email to UAE tax agents

### 1.1 The rules in plain English

**UAE, telecom regulator spam policy.** The regulator's policy defines spam as marketing messages sent without the recipient's consent. Consent is opt-in by default. The policy applies whenever the recipient is in the UAE, even if the message comes from abroad. Its duties are placed on the UAE telecom licensees (du, e&), who must block spam. It does not fine the sender directly, but a cold email to a UAE recipient is "spam" under its definition, and the carriers may block the sender.
- TDRA (then TRA), *Regulatory Policy: Unsolicited Electronic Communications*, Version 1.0, 30 December 2009:
  - Art. 1.11, spam: "Marketing Electronic Communications sent to a Recipient without obtaining that Recipient's Consent".
  - Art. 1.15.4, UAE link: "the Recipient of the Electronic Communication is physically present in the UAE".
  - Art. 1.5, an e-mail address is an "Electronic Address".
  - Art. 3.5, the policy applies to messages that originate "from within or from outside the UAE".
  - Art. 6.8, consent "will always follow an Opt-in Procedure".
  - Art. 6.10: "A means by which a Recipient may Unsubscribe shall be provided".
- TDRA, *Mobile Spam Regulatory Policy* Version 1.1, 13 June 2022: covers text messages only, not e-mail.

**UAE, data protection law (PDPL, Federal Decree-Law 45 of 2021).** A named person's work e-mail is personal data. The law reaches controllers outside the UAE (Art. 2(1)(c)). Processing needs consent unless an exception applies. One exception covers data the person has made public themselves (Art. 4(2)). Every person may object to direct marketing (Art. 17(1)). No source found a business-to-business exemption. The law's Executive Regulations are still not issued as far as any source opened shows.
- Art. 2(1)(c) (Arabic official text, Dubai Judicial Institute edition on u.ae): "كل متحكم أو معالج متواجد خارج الدولة". Translation: "every controller or processor located outside the State".
- Art. 4(2): "أصبحت متاحة ومعلومة للكافة بفعل من صاحب البيانات". Translation: "made available and known to the public by an act of the data subject".
- Art. 17(1): the right to object to processing "لأغراض التسويق المباشر". Translation: "for direct marketing purposes".

**Canada, CASL (S.C. 2010, c. 23).** CASL applies when a computer in Canada is used to send the message, so emails sent by a founder in Canada are covered.
- s.12(1): CASL s.6 applies "only if a computer system located in Canada is used to send or access".
- s.6(1): consent is required, express or implied.
- s.10(9)(b): consent is implied when the address was conspicuously published, carried no "no unsolicited messages" statement, and the message is "relevant to the person's business, role, functions or duties".
- s.6(2): every message must identify the sender, give contact information, and include an unsubscribe mechanism.
- s.11: unsubscribing must be free ("at no cost to them"). The contact details must stay valid "for a minimum of 60 days". Unsubscribe requests must take effect "no later than 10 business days".
- **Foreign-recipient exemption.** Electronic Commerce Protection Regulations, SOR/2013-221, s.3(f): s.6 does not apply when the sender "reasonably believes the message will be accessed in a foreign state that is listed" and the message conforms to that state's law on substantially similar conduct. The schedule lists "United Arab Emirates". The UAE rule above requires opt-in consent, so a cold email cannot be shown to conform to it. **Do not rely on this exemption.** Comply with CASL in full.

### 1.2 What the business must do (only if we send email ourselves)

1. Send only to addresses that the person or their firm published themselves on the firm's own website. Record the URL and date for each address, and confirm the page carries no "no marketing" statement (CASL s.10(9)(b); PDPL Art. 4(2)). An address from the FTA directory does not qualify (see section 3).
2. Write only about their professional role: e-invoicing readiness of their clients.
3. Use the footer of section 9.1 on every message, including follow-ups.
4. Run the unsubscribe from a mailbox or link that works for at least 60 days. Act on every opt-out the same day, and never later than 10 business days. Keep a suppression list for ever.
5. Send at most the 4 messages in Decision section 12's sequence. Stop at the first "no" or opt-out.
6. Keep a send log: address, source URL, date found, messages sent, opt-out date.
7. Treat any reply asking "where did you get my address?" as an objection under PDPL Art. 17: answer with the source, delete the address unless they ask otherwise, and suppress it.

### 1.3 Red lines
- No bought, scraped or harvested lists (TDRA policy Art. 5.7 bans tools for "Address Harvesting").
- No message without the sender's legal name, postal address and a working unsubscribe.
- No message to a personal (non-work) address.
- No "no-reply" sender address on marketing email.

### 1.4 Residual risk: medium if we send, low under the partner model
The UAE policy calls any unconsented marketing email "spam". It is enforced through carriers rather than against senders, and nothing opened shows a fine against a foreign B2B sender. Under the UAE data law, consent is the main basis, and the "made public" exception has not been tested for cold email. CASL itself is satisfied by steps 1 to 4. **[P] Recommended:** we send no cold email ourselves. A UAE partner contacts its own existing contacts (section 8).

---

## 2. LQ-2: marketing calls

### 2.1 Rule
Cabinet Resolution 56 of 2024 regulates marketing by telephone. Resolution 57 of 2024 sets the penalties.
- Official portal u.ae (page updated 02 Sep 2026): one aim is to "Reduce unwanted Marketing Phone Calls".
- The official texts at uaelegislation.gov.ae returned HTTP 403 again on 2026-11-11, so they are **unverified, no source consulted**.
- Secondary (Clyde & Co, 18 Jul 2024, opened 2026-11-11): the rules apply to "all licensed companies in the UAE, including those in free zones". They require prior approval, calls from local numbers under the company's commercial licence, calls only between 9:00 and 18:00, and checks against the Do Not Call Registry.
- Secondary (Pinsent Masons, SRC-31): the rules also cover marketing text messages and social-media messages. Fines go up to AED 150,000.
- TDRA's consumer page "Telemarketing / Voice Spam" (updated 13 Jul 2026) tells consumers to register their number in the DNCR.

### 2.2 What to do
1. Make no marketing calls and send no marketing SMS or WhatsApp messages, from Canada or from anywhere (operational decision already in Decision section 12, kept).
2. Phone calls are allowed only when the prospect asks for one in writing (a booked discovery call). Take those calls during Dubai business hours.
3. If calling ever becomes a channel, only a UAE-licensed partner may do it, under its own approval and numbers, and only after section 11's professional check.

### 2.3 Red lines
- No cold calls.
- No calls from personal numbers.
- No call to a number on the DNCR.

### 2.4 Residual risk: low
We do not call. The question of whether these rules apply to a foreign company or to business-to-business calls stays **unknown** and does not matter while no calls are made.

---

## 3. LQ-3: FTA directory contacts and LinkedIn

### 3.1 Rules
**FTA website terms of use.** Opened 2026-11-11; the page shows Oct 13, 2021, and the site footer shows 11 Nov 2026.
- Users agree not to "collect or store personal information about others" (cl. 2.1.10).
- Users agree not to "post or transmit any unsolicited advertising" (cl. 2.1.8).
- No content may be "downloaded, copied, reproduced, transmitted, stored, sold or distributed" without the FTA's prior written consent. Only personal, non-commercial use is excepted (cl. 9.2).
- **Result:** exporting the Registered Tax Agents directory into a prospect sheet breaches the terms. This is the method execution-plan T-0.1.1 assumed.

**LinkedIn User Agreement**, effective November 3, 2025, s.8.2 "Don'ts":
- Users must not "scrape or copy the Services, including profiles".
- Users must not "Use bots or other unauthorized automated methods" to "add or download contacts, send or redirect messages".
- Users must not send spam.
- Under the UAE telemarketing summaries (section 2), social-media marketing messages may fall within Resolution 56 (secondary source only).

### 3.2 What to do
1. **[P]** Do not take any contact from the FTA directory. You may use the directory only to check, by hand, that a firm is a registered tax agent. Before any outreach, look up the firm's own published contact on its own website and record that URL instead. If the owner wants the directory export anyway, the only route is to ask the FTA for written consent first (cl. 9.2).
2. On LinkedIn, act by hand only. Send a connection request with no sales pitch. Send no automated sequences, export no contacts and use no scraping tools. Write about the topic only after the person accepts or replies.
3. If the person does not answer, send no further LinkedIn message.

### 3.3 Red lines
- No directory export.
- No scraping.
- No automation tools on LinkedIn.
- No sales pitch in a connection request.

### 3.4 Residual risk
- **High** if the FTA directory is exported: the terms clearly forbid it.
- **Medium** for manual LinkedIn contact: it is allowed by LinkedIn's terms, but its treatment under Resolution 56 is unknown.

---

## 4. LQ-4: client invoice data in the UAE, accessed from Canada

### 4.1 Rules (PDPL, Arabic official text)
- **Who does what.** The bookkeeping firm (and through it, its client) decides why the data is processed, so the firm is the controller. We process the data on its instructions, so we are the processor.
- **Art. 8(1).** The processor must process "وفقًا لتعليمات المتحكم" and under the contracts between them. Translation: "according to the controller's instructions".
- **Art. 8, other duties:**
  - delete the data when the processing period ends (8(4));
  - keep a record of processing, including cross-border movement (8(7));
  - prove compliance on request (8(8)).
- **Art. 9(3), breach notice.** A processor that learns of a breach must notify the controller "فور علمه بذلك". Translation: "immediately upon learning of it".
  - The controller then informs the Data Office and the affected people (Art. 9(1), 9(2)).
  - The time limits belong to the Executive Regulations, which are not issued.
- **Art. 22, transfers to an adequate country.** Personal data may leave the UAE to a country whose protection the Data Office approves. No list of approved countries has been published, so Canada has no approval (secondary: Kayrouz & Associates, 3 Feb 2026).
- **Art. 23, other routes.** Without approval, Art. 23(1) allows a transfer on specific grounds. Two of them fit us:
  - (b) the data subject's express consent;
  - (d) a transfer needed to perform a contract between the controller and a third party in the data subject's interest.
  - Art. 23(1)(a), the contract route, is written for countries with no data protection law. Canada has one, so this route does not fit literally.
- **Art. 2(2)(g).** Free-zone firms with their own data law, such as the DIFC and ADGM, fall under that law instead.
- **Inference, not tested.** Viewing UAE-stored data from Canada is probably a "transfer". No source opened settles this.

### 4.2 What the business must do
1. Store every client file and its derived data only in a UAE cloud region: AWS me-central-1, or Azure UAE North or UAE Central. This applies from the first real file (T-0.1.5). **Software rule added in C2:** the application refuses to start in staging or production unless `PINTAE_S3_REGION` is a UAE region. See `packages/core/pintae_core/config.py`, `UAE_STORAGE_REGIONS`, and the test `test_c2_storage_region_must_be_in_the_uae_outside_local`. The database host must be in the same region (TRD section 7, unchanged).
2. Synthetic data first. Run free checks and demos on the synthetic fixtures FX-A to FX-E, never on real files. A real file is accepted only under a signed pilot agreement that contains the clauses of section 9.3.
3. Reduce access from Canada:
   - files are opened only inside a UAE-region virtual desktop, never downloaded (T-0.1.5, unchanged);
   - one named person has access, with multi-factor sign-in;
   - every access is logged.
4. Cover the remaining access from Canada in the pilot agreement, on two grounds:
   - Art. 23(1)(d): the firm instructs it as necessary for the service it contracted for its clients;
   - the firm confirms it has its clients' authority to share the data.
   The firm, not us, deals with its clients.
5. Do not ask for files that name individuals unless a check needs them. Customer names of businesses are enough for RC-01 to RC-20. Advise firms to remove individuals' columns they do not need.
6. Deletion: delete on the firm's written choice, at the latest 30 days after the pilot ends (or the retention period in schema.md, whichever is shorter), and log the deletion (Art. 8(4)).
7. Breach: tell the firm within 24 hours of learning of a breach. Give what we know: what happened, which data, how many records, what we did (Art. 9(1)(a) to (e) list). The firm notifies the Data Office and the people affected.
8. Keep the Art. 8(7) record: firm, data categories, who has access, period, deletion method, and the "accessed from Canada by one named person through a UAE virtual desktop" note.

### 4.3 Red lines
- No client file on a laptop or in any region outside the UAE.
- No real file in a demo.
- No file without a signed agreement.
- No individual's data that the check does not need.
- No use of client data for anything except the firm's checks, including outreach and training.

### 4.4 Residual risk: medium
The law is clear on the processor's duties, and the steps follow them. Two things stay uncertain:
- whether remote viewing from Canada counts as a transfer;
- whether Art. 23(1)(d) covers it.
The Executive Regulations, which would set breach time limits and transfer conditions, are not issued. **[P] Lower-risk option (section 8, model A):** move to self-serve, where the firm runs the tool and we never open its files.

---

## 5. LQ-5: "not an ASP" wording and registration with the FTA or MoF

### 5.1 Rules
**Ministerial Decision 168 of 2026** on accreditation of service providers (effective 1 October 2026). It repeals Ministerial Decision 64 of 2025 (Art. 18).
- Art. 1 defines Electronic Invoicing Services as "The service of sending, receiving and exchanging Electronic Invoices" (and credit notes and related documents) under the Peppol framework.
- Art. 3(1): a service provider may provide Electronic Invoicing Services "in the State after obtaining Accreditation".

**Ministerial Decision 243 of 2025**, Art. 5: the issuer and the recipient of invoices must appoint an Accredited Service Provider from the Ministry's published list.

**Result.** A readiness check that reads exports and lists gaps does not send, receive or exchange e-invoices. It is therefore not an Electronic Invoicing Service and needs no accreditation.

Nothing opened requires an FTA or MoF registration for selling software or data checks. Representing a taxpayer before the FTA is a tax-agent function; the product never does it, and the firm's Reviewer is the tax agent. **This last point is unverified:** the Tax Procedures law was not opened.

### 5.2 What to do
1. Put the disclaimer of section 9.4 on the website, every report and every outreach message.
2. Never transmit, convert into, or produce e-invoice XML, and never connect to Peppol, the FTA or an ASP (AGENTS.md section 3, unchanged).
3. Never say or suggest that a result is accepted by the FTA, the MoF or any ASP. The words "compliant", "validated", "approved" and "certified" stay banned (CLAUDE.md).
4. Never file, submit or correct anything with the FTA for a client.
5. Re-check MD 168 and the MoF e-invoicing page every week (T-0.1.7). If the definition widens to include "validation" or "data preparation" services, stop selling and re-assess.

### 5.3 Red lines
- No transmission.
- No XML.
- No accreditation claims.
- No acting for a taxpayer before the FTA.

### 5.4 Residual risk: low
The definition is narrow and clear, and we stay outside it.

---

## 6. Trade licence for a foreign company selling software remotely

### 6.1 Rule
Commercial Companies Law, Federal Decree-Law 32 of 2021 (English text on the Ministry of Economy site):
- Art. 336(1): "foreign companies may not conduct an activity inside the State" without a licence.
- Art. 337(1): a foreign company must also be entered in the Foreign Companies Register.
- Art. 336(2): people who act before licensing are "severally and jointly liable".
- Art. 339(1): a representative office may only study markets.
- The law was amended in 2025 (Federal Decree-Law 20 of 2025, secondary); the amended text was not read.

The law does not define whether remote sales from Canada, with no UAE office, staff or agent, are an "activity inside the State". **Unknown.**

### 6.2 What to do
1. Keep no UAE office, staff, agent, bank account, phone number or address.
2. Contracts are made and signed by the Canadian company, in Canada. Invoices are issued from Canada.
3. The UAE partner of section 8 is independent. It does not sign contracts or take orders in our name, it is paid a referral fee, and it is not our agent. This avoids a UAE presence and lowers the corporate-tax permanent-establishment risk (secondary, not opened).
4. **[P]** If UAE revenue passes the point where licensing costs less than the risk, register through a free-zone or mainland licence. Section 11 sets the trigger.

### 6.3 Red lines
- No one in the UAE signs or negotiates for us.
- No local office or "UAE branch" wording on the website.

### 6.4 Residual risk: medium
The rule text is clear. Its application to purely remote software sales is not.

---

## 7. VAT on the invoices we issue

### 7.1 Rules
Federal Decree-Law 8 of 2017 and its amendments (MoF consolidated text, published 28 Nov 2025):
- Art. 29: the default place of supply of services is where the supplier resides (Canada).
- Art. 30(2) changes this when "the Recipient of Services is in Business and has a Place of Residence in the State". Then the place of supply is the UAE.
- Art. 48(1): a business that imports services must account for the VAT itself. It "shall be responsible for accounting for the Due Tax".

FTA E-Commerce VAT Guide (VATGEC1, 2020), section 4.4:
- The reverse charge applies when the recipient is registered or required to register.
- If the supplier cannot confirm this, "the responsibility to account for VAT remains with the supplier".

### 7.2 What to do
1. Sell only to firms with a UAE TRN. Before the first invoice, check the TRN on the FTA's TRN verification service and keep a screenshot.
2. Put the reverse-charge note of section 9.5 on every invoice. Charge no UAE VAT.
3. Do not sell to a firm that is not VAT-registered until the treatment is checked (section 11).
4. **Canadian side, not researched:** GST/HST on exported services and the Canadian invoicing entity are open (Decision section 11, item 6).

### 7.3 Red lines
- No invoice without the client's verified TRN on file.
- No UAE VAT line, because we are not registered.

### 7.4 Residual risk
- **Low** for VAT-registered firms. Bookkeeping firms that are tax agents are normally registered; this was not verified per firm.
- **Medium** otherwise: a non-registered recipient may leave the supplier liable to register.

---

## 8. The no-lawyer operating model `[P]`

Owner decisions to sign. These change how we sell and deliver, not what the product checks.

1. **A UAE partner does outreach under its own licence.** The partner is an accounting firm, an Odoo or Zoho partner, or an Accredited Service Provider.
   - It writes only to its own existing clients and contacts, with whom it already has a relationship, under its UAE trade licence and its own consent records.
   - We never receive its contact list.
   - It sends the referral wording of section 9.2. Interested firms come to us by replying or booking a call (inbound), which is consented contact.
   - The partner earns a referral fee per paid pilot.
   - **Not modelled:** the fee changes the economics of Decision section 7 and must be re-run there before any agreement.
   - Effects: CASL does not apply to messages sent from UAE systems (s.12(1)); the TDRA consent question becomes the partner's existing-relationship question; the FTA directory is not used.
2. **Email only, with clear sender identity and opt-out.** Any email we send ourselves follows section 1.2. No calls, SMS, WhatsApp or automated LinkedIn.
3. **Data hosted in the UAE region**, enforced by the start-up check of section 4.2, step 1. Access from Canada only through the UAE virtual desktop.
4. **Synthetic demo first.** Every first meeting and free check uses FX-A to FX-E or the firm's own anonymised sample. A real file comes only after a signed pilot agreement.
5. **Later, lower risk (model A, self-serve).** When the application exists (Phase 2 onward), the firm uploads and runs checks itself in the UAE-region application. Vendor staff see tenant data only through an Owner's grant (AGENTS.md section 5, unchanged), so the Canadian access question mostly disappears.

---

## 9. Templates (template - adapt)

### 9.1 Email footer
> [Founder name], [Company legal name], [postal address, city, province, Canada]. [email] · [website]
> You are receiving this because your work address is published on [source website] and this message concerns e-invoicing readiness of your clients. Reply "stop" or use [unsubscribe link] and you will get no further messages; we act on it the same day.
> We are not an Accredited Service Provider and do not transmit e-invoices.

### 9.2 Partner referral wording (sent by the partner to its own contacts)
> Subject: A data check before your clients appoint an e-invoicing provider
>
> Dear [name], as your [accountant / Odoo partner / ASP], we are sharing a tool that may help with the 31 March 2027 appointment date. [Company] checks a client's Excel, QuickBooks or Odoo exports against the PINT AE mandatory fields and returns a fix list. It shows data gaps only; it does not decide whether a client will meet a deadline, and [Company] is not an Accredited Service Provider. [Company] is an independent company in Canada; we receive a referral fee if you buy. If you are interested, reply to us or book at [link]; we will not pass your details on unless you ask. To stop these updates from us, reply "stop".
> [Partner legal name, licence number, address]

### 9.3 Data handling notice and pilot agreement clauses
> **Data handling (template - adapt).**
> 1. *Roles.* The Firm decides what data is shared and why and is the controller; [Company] processes it only on the Firm's written instructions to run the readiness checks in this agreement.
> 2. *Authority.* The Firm confirms it has its clients' authority to share their exports for this purpose.
> 3. *Location.* Files and results are stored only in [AWS me-central-1 / Azure UAE North], United Arab Emirates. One named [Company] person, [name], may view them from Canada only through a virtual desktop in that region; files are not downloaded outside it. The Firm instructs this access as necessary for the service.
> 4. *Minimum data.* The Firm will remove columns about individuals that the checks do not need.
> 5. *Use.* The data is used only for the Firm's checks: not for marketing, not for training any model, not shared with anyone else.
> 6. *Security.* Encryption at rest, no public access, multi-factor sign-in, access logs.
> 7. *Deletion.* Deleted on the Firm's written request, and in any case within 30 days after the pilot ends; deletion is logged and confirmed in writing.
> 8. *Breach.* [Company] tells the Firm within 24 hours of learning of a breach, with what happened, which data, how many records and what was done.
> 9. *Records.* [Company] keeps a record of this processing and gives it to the Firm on request.
> 10. *Not an ASP.* Clause 9.4 applies.

### 9.4 "Not an ASP" disclaimer
> [Company] is not an Accredited Service Provider under the UAE Electronic Invoicing System (Ministerial Decision 168 of 2026). It does not send, receive or exchange e-invoices, does not produce e-invoice files, and is not connected to the FTA, the Ministry of Finance, Peppol or any provider. Results show data gaps against the rule pack version stated; they are not an approval by any authority or provider, and they do not show whether a client will meet any legal deadline. "Data-ready" means no open gap under that rule pack version.

### 9.5 Invoice note (VAT)
> Supplier not registered for VAT in the UAE. Recipient TRN [TRN]. Reverse charge: the recipient accounts for UAE VAT under Article 48 of Federal Decree-Law No. 8 of 2017.

---

## 10. Red lines in one list

1. No cold calls, SMS or WhatsApp marketing.
2. No contacts exported from the FTA directory; no scraping; no bought lists; no LinkedIn automation.
3. No marketing email without sender identity, postal address and a working opt-out; no further message after an opt-out.
4. No client file outside a UAE region, on a laptop, or before a signed agreement; no real data in demos.
5. No e-invoice transmission, XML, Peppol connection or accreditation claim; no "compliant", "validated" or "approved".
6. No one in the UAE contracting for us; no UAE office or branch wording.
7. No invoice to a UAE firm without its verified TRN.

## 11. When to get professional help anyway

Get a UAE-qualified lawyer, or a UAE tax adviser for item 6, before acting if any of these happens:
1. A complaint, a regulator letter (TDRA, the Data Office or Federal Authority for AI and Data, FTA, MoF, Ministry of Economy), or a carrier blocking our domain.
2. A data breach or suspected exposure of a client file.
3. A firm's or partner's contract demands legal warranties, indemnities, a data processing agreement on their paper, or names a governing law other than the one we offered.
4. The PDPL Executive Regulations are issued (they may set transfer and breach rules that change section 4).
5. We plan calls, SMS, WhatsApp or automated LinkedIn, or a partner proposes to do them for us.
6. We plan to sell to firms that are not VAT-registered, to hire anyone in the UAE, or UAE revenue passes AED 375,000 in 12 months (the UAE VAT registration threshold for residents, used here only as a size trigger, not a legal rule for us).
7. MD 168 or a new decision widens "Electronic Invoicing Services", or the FTA or MoF publishes rules for "readiness" or "pre-validation" providers.
8. A firm in the DIFC or ADGM asks to become a customer (their own data laws apply; not researched).

## 12. Sources opened 2026-11-11

| ID | Source | Used for |
|---|---|---|
| CS-01 | TDRA, Regulatory Policy Unsolicited Electronic Communications v1.0, 30 Dec 2009: https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/Unsolicited-Elrctronic-Commuincations--pdf.ashx | Spam definition, UAE link, opt-in, unsubscribe |
| CS-02 | TDRA, Mobile Spam Regulatory Policy v1.1, 13 Jun 2022: https://tdra.gov.ae/-/media/About/regulations-and-ruling/EN/cellular-phone-spam-regulatory-policy-English.ashx | Scope is text messages |
| CS-03 | TDRA, Telemarketing / Voice Spam (updated 13 Jul 2026): https://tdra.gov.ae/en/consumer-tool-hub/topics/telemarketing-voice-spam | DNCR |
| CS-04 | u.ae, Consumer protection (updated 02 Sep 2026): https://u.ae/en/information-and-services/justice-safety-and-the-law/consumer-protection | Resolution 56 aims |
| CS-05 | Clyde & Co, 18 Jul 2024 (secondary): https://www.clydeco.com/en/insights/2024/07/uae-tightens-telemarketing-regulations-what-you-ne | Resolution 56 scope, hours, numbers, approval |
| CS-06 | Federal Decree-Law 45 of 2021 (PDPL), Arabic, Dubai Judicial Institute edition 2023, linked from u.ae data protection page: https://assets.u.ae/api/public/content/954629a06cc64fd887771ce3273d6154?v=21d88839 | Arts 2, 4, 8, 9, 17, 22, 23 |
| CS-07 | u.ae, Data protection laws (updated 04 Dec 2025): https://u.ae/en/about-the-uae/digital-uae/data/data-protection-laws | PDPL summary |
| CS-08 | Justice Laws, CASL S.C. 2010 c. 23, current to 2026-10-19: https://laws-lois.justice.gc.ca/eng/acts/E-1.6/FullText.html | ss. 6, 10(9), 11, 12 |
| CS-09 | Justice Laws, Electronic Commerce Protection Regulations SOR/2013-221: https://laws-lois.justice.gc.ca/eng/regulations/SOR-2013-221/FullText.html | s.3(f) and schedule (UAE listed) |
| CS-10 | FTA website Terms & Conditions: https://www.tax.gov.ae/en/content/terms.conditions.aspx | cl. 2.1.8, 2.1.10, 9.2 |
| CS-11 | LinkedIn User Agreement, effective 3 Nov 2025: https://www.linkedin.com/legal/user-agreement | s.8.2 |
| CS-12 | MoF, Ministerial Decision 168 of 2026 (effective 1 Oct 2026): https://mof.gov.ae/wp-content/uploads/2026/10/Ministerial-Decision-No-168-of-2026-on-Eligibility-criteria-and-Accreditation-Procedure-EN-FINAL.pdf | Arts 1, 3, 18 |
| CS-13 | MoF, Ministerial Decision 243 of 2025: https://mof.gov.ae/wp-content/uploads/2025/09/Ministerial-Decision-no.-243-of-2025-on-the-Electronic-Invoicing-System.pdf | Art. 5 |
| CS-14 | Ministry of Economy, Federal Decree-Law 32 of 2021 (Lexis English text): https://www.moet.gov.ae/documents/20121/376326/Commercial+Companies.pdf/12d14f53-1a3e-47b4-8e70-fac3f672c403?t=1645596097819 | Arts 335 to 339 |
| CS-15 | MoF/FTA, Federal Decree-Law 8 of 2017 and amendments (published 28 Nov 2025): https://tax.gov.ae/Datafolder/Files/Legislation/2025/Federal%20Decree-Law%20No.%208%20of%202017%20and%20amendments%20-%20publishing%2028%2011%202025.pdf | Arts 29, 30(2), 48(1) |
| CS-16 | FTA, E-Commerce VAT Guide VATGEC1 (2020): https://tax.gov.ae/DownloadOpenTextFile?fileUrl=en%2FVAT_VAT_Guides%2FE_Commerce%2FE_Commerce_VAT+Guide_EN_09_08_2020_EN.pdf | s.4.4 reverse charge conditions |
| CS-17 | Kayrouz & Associates, 3 Feb 2026 (secondary, from C1, not re-opened): https://www.kayrouzandassociates.com/insights/cross-border-data-transfers-under-uae-law-in-2026 | No adequacy list |

## 13. Not verified

- Official texts of Cabinet Resolutions 56 and 57 of 2024 and the English PDPL at uaelegislation.gov.ae: HTTP 403 (bot verification) on 2026-11-11, not bypassed. **Unverified, no source consulted** for the primary text; secondary summaries used and labelled.
- PDPL Executive Regulations: no official source shows them issued (search 2026-11-11; Morgan Lewis 15 Jun 2026 and BusinessDubai Aug 2026 say not issued).
- Whether viewing UAE-stored data from Canada is a "transfer" under PDPL Art. 22/23.
- Whether Resolution 56 covers foreign companies, B2B calls or LinkedIn messages.
- Whether remote software sales are an "activity inside the State" (CCL Art. 336); the 2025 amendments were not read.
- The Tax Procedures law on tax-agent functions; Canadian GST/HST on exported services; PIPEDA duties of the Canadian company; DIFC and ADGM data laws.
