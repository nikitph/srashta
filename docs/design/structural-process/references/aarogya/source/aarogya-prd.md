# Aarogya Billing — Product Requirements Document

Version 0.1 · Draft · 20 September 2026 · Owner: Amul Rangnekar
Reviewers: hospital finance lead, insurance desk lead, legal (tax and data protection), engineering

## Document control

| Version | Date | What changed |
|---|---|---|
| 0.1 | 2026-09-20 | First complete draft: core revenue cycle for Indian hospitals, multitenant. |

| Audience | Read |
|---|---|
| Business and hospital operations | Parts I, II; sections 6 to 12 |
| Finance | Sections 9 to 11, 14, 15; Appendix B |
| Legal (GST, income tax, data protection) | Sections 10, 13, 16, 17; Part V |
| Engineering and agents | Everything; Appendices B to E are test oracles |

## Requirement conventions

Identifiers are `FR-DOMAIN-NNN` and `NFR-NNN`, and are **permanent**: a dropped requirement is
marked withdrawn, never renumbered.

| Priority | Meaning | Test for inclusion |
|---|---|---|
| P0 | Minimum viable | A hospital cannot bill, collect, or claim lawfully without it. |
| P1 | Fast follow | Its absence is felt as manual work or friction, not as a failed or unlawful bill. |
| P2 | Later | Listed so the data model does not foreclose it. |

`must` binds. `should` is a strong default, tradeable with a recorded rationale. `may` is an
option retained for later. Monetary amounts are in Indian rupees; "Rs" means rupees. Times are
Indian Standard Time unless stated. A financial year runs 1 April to 31 March.

# Part I — Context

## 1 Problem statement

Small and mid-sized Indian hospitals (20 to 300 beds) bill on desktop software or spreadsheets
that do not know the rules they operate under. Room rent above a daily threshold is taxable while
the rest of the stay is exempt. Insurers must decide cashless pre-authorisation within one hour
and discharge authorisation within three, but the hospital has no clock running on its side, so
patients wait at discharge. Government schemes forbid charging the beneficiary anything, yet
itemised charges leak onto their bills. Deposits are taken in cash with no link to the final
bill, and refunds are settled from memory.

Aarogya Billing is a multitenant web product that runs a hospital's revenue cycle from
registration to settled claim: one encounter account per visit, tariffs that know the payer,
bills that are correct under GST by construction, and a claims desk that runs against the
payer's clock.

## 2 Actors and personas

| Actor | Who | Wants |
|---|---|---|
| Front-desk registrar | Registers patients, opens encounters | A fast, duplicate-free registration |
| Cashier | Takes deposits and payments, issues receipts, closes a shift | Receipts that tie to bills; a shift that reconciles |
| Billing executive | Posts charges, prepares interim and final bills, applies discounts | A final bill that is right the first time |
| Insurance desk executive | Pre-authorisation, discharge authorisation, claims, queries | To know which case is about to breach a payer deadline |
| Finance manager | Receivables, write-offs, doctor fee payouts, GST returns | Numbers that reconcile to the ledger |
| Hospital administrator | Configures the hospital: facilities, tariffs, users, payers | Configuration without a vendor call |
| Patient or payer of the bill | Receives estimates, bills, receipts, refunds | To know what they owe and why |
| Platform operator | Runs the SaaS: provisions tenants, supports them | Tenants isolated from each other; incidents contained |

## 3 Primary journeys

| Id | Journey |
|---|---|
| J1 | OPD visit: register or find the patient, open a visit, post consultation and investigations, collect payment, issue a receipt |
| J2 | Planned cash admission: estimate, deposit, admission, daily charges, interim bill, final bill, settlement against deposit, refund of excess |
| J3 | Cashless insured admission: pre-authorisation, enhancement, discharge authorisation, patient share collected, claim submitted, settled with deductions |
| J4 | Government scheme admission (PM-JAY or CGHS): package booked, nothing charged to the beneficiary, claim submitted within the scheme window |
| J5 | Cashier shift: open, collect, hand over, close, reconcile with variance explained |
| J6 | Month end: receivables ageing, doctor fee payouts with TDS, GST summary for the return |

## 4 Success metrics

| Metric | Target |
|---|---|
| Final bills corrected after issue (credit note within 7 days) | under 2% of final bills |
| Discharge-to-bill time for cash patients | median under 30 minutes |
| Cashless cases where the hospital-side deadline was breached | under 5% |
| Claims submitted after the payer's window | 0 for schemes; under 2% for insurers |
| Cashier shifts closed with an unexplained variance | 0 |

# Part II — Scope

## 5 Scope

### 5.1 In scope for v1
Tenancy, facilities and GST registrations; staff accounts and facility-scoped roles; patient
registration with ABHA capture; encounters (OPD, IPD, day care, emergency) with room-category
history; tariffs, price lists and packages; charge capture, including an inbound charge interface
for clinical systems; interim and final bills; GST treatment; e-invoice registration where the
tenant is obliged; deposits, payments, receipts and refunds; cashier shifts; payers and payer
contracts; pre-authorisation, discharge authorisation and claims; doctor fee share with TDS;
receivables; notifications; audit; reports.

### 5.2 Explicitly deferred
- Clinical documentation, orders, pharmacy dispensing, laboratory and bed management. Aarogya
  receives charges from those systems; it does not run them.
- Inventory and procurement.
- Payroll. Salaried doctors are out of scope for TDS; only fee-share payees are covered.
- A patient-facing mobile app. Patients receive documents by message and link.
- Automated claim submission to individual TPA portals. Claims to TPAs are prepared here and
  recorded as submitted; only NHCX is an automated channel (P1).
- Billing the tenants for the SaaS subscription.
- Markets outside India.

### 5.3 Dependencies and external assumptions
- A payment gateway for card and UPI collection, with a webhook for asynchronous confirmation.
- An SMS provider registered on the TRAI DLT platform, and a WhatsApp Business provider.
- The GST e-invoice registration portal (IRP), for tenants above the e-invoice turnover threshold.
- NHCX (National Health Claims Exchange) for claims, P1; ABDM gateway for ABHA verification.
- Clinical systems that can call an inbound HTTP interface to post charges.
- An accounting system (Tally or similar) that imports a voucher file.
# Part III — Functional requirements

## 6 Tenancy and organisation

A tenant is one hospital business: one legal entity or group. It has one or more facilities
(a hospital, a clinic, a day-care centre), each registered under one GSTIN. Everything a
tenant creates belongs to that tenant and to nothing else.

FR-TEN-001 [P0]
Every record created on the platform must belong to exactly one tenant, and no request may read or change another tenant's records.

Acceptance criteria
  THE SYSTEM SHALL associate every stored business record with exactly one tenant.
  IF a request from a member of one tenant names a record of another tenant THEN THE SYSTEM SHALL respond as if the record does not exist.
  THE SYSTEM SHALL NOT include another tenant's records in any list, search, report or export.

Rationale
  One leaked bill is a data-protection breach for the hospital and the end of the product.
  This rule applies to every domain in this document, including ones added later.

FR-TEN-002 [P0]
A platform operator must be able to provision a tenant with its legal name, PAN and a first administrator.

Acceptance criteria
  WHEN a platform operator provisions a tenant THE SYSTEM SHALL create the tenant in the provisioning state with its legal name and PAN.
  WHEN a tenant is provisioned THE SYSTEM SHALL invite the named first administrator.
  IF the PAN is not in the valid PAN format THEN THE SYSTEM SHALL refuse the provisioning.

FR-TEN-003 [P0]
A tenant administrator must be able to add a facility with its name, address, state and facility type.

Acceptance criteria
  WHEN an administrator adds a facility THE SYSTEM SHALL record its name, address, state and type.
  THE SYSTEM SHALL accept facility types hospital, clinic and day-care centre.

FR-TEN-004 [P0]
Each facility must be linked to one GST registration, and a GST registration may serve several facilities in the same state.

Acceptance criteria
  WHEN an administrator links a facility to a GSTIN THE SYSTEM SHALL check that the GSTIN's state code matches the facility's state.
  IF the GSTIN's state code differs from the facility's state THEN THE SYSTEM SHALL refuse the link.
  IF the GSTIN does not embed the tenant's PAN THEN THE SYSTEM SHALL refuse the link.

FR-TEN-005 [P0]
A tenant must be able to record, per financial year, whether it is obliged to register e-invoices and to print a dynamic QR code on consumer invoices.

Acceptance criteria
  WHEN an administrator records the prior-year aggregate turnover THE SYSTEM SHALL derive the e-invoice and dynamic-QR obligations from the configured thresholds.
  THE SYSTEM SHALL keep the obligation per financial year so that a change applies from the year it was recorded for.

FR-TEN-006 [P0]
A tenant must be able to define document number series per GSTIN per financial year for each document type.

Acceptance criteria
  THE SYSTEM SHALL keep a separate number series per GSTIN, per financial year, per document type.
  IF a configured series format can produce a number longer than 16 characters THEN THE SYSTEM SHALL refuse the series.
  WHEN a financial year begins THE SYSTEM SHALL start each series of that year from its first number.

Rationale
  Rule 46(b) of the CGST Rules limits a serial number to 16 characters and requires it to be unique for a financial year.

FR-TEN-007 [P0]
A platform operator must be able to suspend a tenant, after which its members can sign in only to export their data.

Acceptance criteria
  WHEN a platform operator suspends a tenant with a recorded reason THE SYSTEM SHALL move the tenant to suspended.
  WHILE a tenant is suspended THE SYSTEM SHALL refuse every action except sign-in and data export.

FR-TEN-008 [P1]
A tenant must be able to be offboarded, with its data exported and then erased after the retention period.

Acceptance criteria
  WHEN a platform operator offboards a tenant THE SYSTEM SHALL produce a complete export of the tenant's records.
  WHEN the retention period for the tenant's records ends THE SYSTEM SHALL erase them.
  THE SYSTEM SHALL NOT erase records whose retention period has not ended.

FR-TEN-009 [P0]
A tenant administrator must be able to set the tenant's working configuration: state, default facility, financial-year start and rounding rule.

Acceptance criteria
  WHEN an administrator saves the tenant configuration THE SYSTEM SHALL validate it against the configuration schema.
  IF a configuration value is outside its permitted range THEN THE SYSTEM SHALL refuse it and name the value.

## 7 Accounts

Staff accounts only; patients do not sign in to v1.

FR-ACC-001 [P0]
A person invited by a tenant administrator must be able to create a staff account from the invitation.

Acceptance criteria
  WHEN an invitee opens a valid invitation THE SYSTEM SHALL let them set a password and create the account.
  IF the invitation has expired or been used THEN THE SYSTEM SHALL refuse it.

FR-ACC-002 [P0]
A staff member must be able to sign in with an email address and password.

Acceptance criteria
  WHEN a staff member supplies correct credentials THE SYSTEM SHALL start a session.
  IF sign-in fails five times within fifteen minutes for one account THEN THE SYSTEM SHALL lock the account for fifteen minutes.

FR-ACC-003 [P0]
Multi-factor authentication must be required for administrators, finance managers and platform operators.

Acceptance criteria
  IF a staff member holding a role that requires multi-factor authentication has not enrolled THEN THE SYSTEM SHALL require enrolment before any other action.
  WHEN such a staff member signs in THE SYSTEM SHALL require the second factor.

FR-ACC-004 [P0]
A staff member must be able to reset a forgotten password by a single-use link.

Acceptance criteria
  WHEN a reset is requested THE SYSTEM SHALL send a link valid for 60 minutes.
  IF the link has been used or has expired THEN THE SYSTEM SHALL refuse it.
  THE SYSTEM SHALL NOT disclose whether an email address has an account.

FR-ACC-005 [P0]
A staff account may belong to more than one tenant, and a session must act within exactly one tenant at a time.

Acceptance criteria
  WHEN a staff member belonging to several tenants signs in THE SYSTEM SHALL ask which tenant to act in.
  WHILE a session acts in one tenant THE SYSTEM SHALL scope every request to that tenant.

Rationale
  Consultants and billing agencies work for several hospitals.

FR-ACC-006 [P0]
A tenant administrator must be able to deactivate a staff member's membership, ending their sessions in that tenant.

Acceptance criteria
  WHEN an administrator deactivates a membership THE SYSTEM SHALL end every session of that person acting in that tenant.
  WHILE a membership is deactivated THE SYSTEM SHALL refuse sign-in to that tenant.

FR-ACC-007 [P1]
A staff member must be able to see and revoke their own active sessions.

Acceptance criteria
  WHEN a staff member revokes a session THE SYSTEM SHALL refuse any further request made with it.

FR-ACC-008 [P0]
A session must expire after a period of inactivity set by the tenant.

Acceptance criteria
  WHEN a session has been inactive for the tenant's configured period THE SYSTEM SHALL end it.

## 8 Access control

Roles are granted per facility. A role is a named set of permissions; the permission list is
fixed by the product and the tenant composes roles from it.

FR-AUTHZ-001 [P0]
A tenant administrator must be able to grant a role to a member for one or more facilities.

Acceptance criteria
  WHEN an administrator grants a role for a facility THE SYSTEM SHALL let the member exercise that role's permissions only in that facility.
  THE SYSTEM SHALL require a recorded reason for every grant and revocation.

FR-AUTHZ-002 [P0]
Every action must be permitted only when the acting member holds a permission for it in the facility the action concerns.

Acceptance criteria
  IF a member attempts an action without the permission for that facility THEN THE SYSTEM SHALL refuse it.
  THE SYSTEM SHALL check the permission in the application action, not only by hiding the control.

Rationale
  This rule applies to every action in this document.

FR-AUTHZ-003 [P0]
The product must ship the default roles registrar, cashier, billing executive, insurance executive, finance manager and administrator.

Acceptance criteria
  WHEN a tenant is provisioned THE SYSTEM SHALL create the default roles with the permissions in Appendix D.

FR-AUTHZ-004 [P1]
A tenant administrator must be able to define a custom role from the product's permission list.

Acceptance criteria
  WHEN an administrator saves a custom role THE SYSTEM SHALL accept only permissions from the product's list.

FR-AUTHZ-005 [P0]
Actions marked as needing approval must be completed only after a second member with approval permission approves them.

Acceptance criteria
  WHEN a member requests an action that needs approval THE SYSTEM SHALL hold it pending until approved or rejected.
  IF the approver is the requester THEN THE SYSTEM SHALL refuse the approval.
  THE SYSTEM SHALL apply this to discounts above the member's limit, refunds, bill cancellation and write-offs.

FR-AUTHZ-006 [P0]
A tenant administrator must be able to set, per role, the largest discount a member may give without approval.

Acceptance criteria
  IF a discount exceeds the acting member's limit THEN THE SYSTEM SHALL route it for approval.

FR-AUTHZ-007 [P1]
A platform operator must be able to act inside a tenant for support only with the tenant's time-limited consent.

Acceptance criteria
  IF no unexpired support consent exists for the tenant THEN THE SYSTEM SHALL refuse the operator's access.
  WHILE an operator acts inside a tenant THE SYSTEM SHALL mark every action as taken under support access.
## 9 Patients

FR-PAT-001 [P0]
A registrar must be able to register a patient with name, sex, date of birth or age, mobile number and address.

Acceptance criteria
  WHEN a registrar registers a patient THE SYSTEM SHALL assign a unique hospital identifier (UHID) within the tenant.
  IF only an age is given THEN THE SYSTEM SHALL record an estimated date of birth and mark it estimated.

FR-PAT-002 [P0]
Registration must warn of a probable duplicate before a new patient is created.

Acceptance criteria
  WHEN a new registration matches an existing patient on mobile number and name similarity above the configured threshold THE SYSTEM SHALL show the candidates before creating a patient.
  WHEN the registrar confirms the new patient is distinct THE SYSTEM SHALL record that confirmation.

FR-PAT-003 [P1]
A billing executive must be able to merge two patient records that are the same person.

Acceptance criteria
  WHEN two patients are merged THE SYSTEM SHALL move every encounter, bill and receipt of the merged record to the surviving record.
  WHEN two patients are merged THE SYSTEM SHALL keep the merged UHID resolvable to the surviving record.
  THE SYSTEM SHALL NOT merge two patients who each have an encounter in progress.

FR-PAT-004 [P1]
A registrar must be able to link a patient's ABHA number or address after verifying it with the ABDM gateway.

Acceptance criteria
  WHEN a registrar submits an ABHA identifier THE SYSTEM SHALL verify it with the ABDM gateway before linking it.
  IF verification fails THEN THE SYSTEM SHALL refuse the link and state the gateway's reason.

FR-PAT-005 [P0]
A patient's identity documents for payers must be recorded with type and number, with only the last four characters shown after entry.

Acceptance criteria
  WHEN an identity document number is saved THE SYSTEM SHALL display only its last four characters thereafter.
  THE SYSTEM SHALL store identity document numbers encrypted.

FR-PAT-006 [P0]
A patient's payer entitlements must be recorded: insurer or TPA policy, scheme beneficiary identifier, or corporate employee identifier.

Acceptance criteria
  WHEN an entitlement is recorded THE SYSTEM SHALL require the payer, the member identifier and the validity period.
  IF an entitlement's validity period has ended THEN THE SYSTEM SHALL not offer it for a new encounter.

FR-PAT-007 [P0]
A patient's consent to the hospital's privacy notice must be recorded at registration with the notice version.

Acceptance criteria
  WHEN a patient is registered THE SYSTEM SHALL record the privacy-notice version shown and the time consent was given.
  IF consent is not given THEN THE SYSTEM SHALL register the patient only for emergency treatment and mark the record accordingly.

## 10 Encounters

An encounter is one episode of care that is billed as a unit: an OPD visit, an in-patient
admission, a day-care procedure or an emergency visit.

FR-ENC-001 [P0]
A registrar must be able to open an OPD visit for a patient at a facility.

Acceptance criteria
  WHEN a registrar opens an OPD visit THE SYSTEM SHALL create an encounter of type OPD in the open state for that facility.
  THE SYSTEM SHALL assign the encounter a number unique within the facility.

FR-ENC-002 [P0]
A registrar must be able to admit a patient as an in-patient with an admitting doctor, a room category and a financial class.

Acceptance criteria
  WHEN a patient is admitted THE SYSTEM SHALL create an encounter of type IPD in the admitted state.
  THE SYSTEM SHALL require the financial class cash, insured, scheme or corporate at admission.
  IF the financial class is insured, scheme or corporate THEN THE SYSTEM SHALL require one of the patient's valid entitlements.

FR-ENC-003 [P0]
Every change of room category during a stay must be recorded with the time it took effect.

Acceptance criteria
  WHEN the room category changes THE SYSTEM SHALL close the current room period and open a new one at the recorded time.
  THE SYSTEM SHALL keep the room periods of an encounter contiguous and non-overlapping.

Rationale
  Room rent, its GST treatment and insurer proportionate deductions all depend on the room category per day.

FR-ENC-004 [P0]
A billing executive must be able to change an encounter's financial class before the final bill.

Acceptance criteria
  WHEN the financial class changes THE SYSTEM SHALL re-price every open charge line under the new payer.
  IF a final bill exists for the encounter THEN THE SYSTEM SHALL refuse the change.

FR-ENC-005 [P0]
A doctor's discharge order must move an in-patient encounter to discharge initiated.

Acceptance criteria
  WHEN a discharge is initiated THE SYSTEM SHALL record the time and move the encounter to discharge initiated.
  WHEN a discharge is initiated for an insured cashless encounter THE SYSTEM SHALL start the discharge-authorisation clock of FR-CLM-009.

FR-ENC-006 [P0]
An in-patient encounter must be marked discharged only after its final bill is settled or its balance is accepted as due.

Acceptance criteria
  IF the final bill has an unsettled patient balance that no authorised member accepted as due THEN THE SYSTEM SHALL refuse the discharge.
  THE SYSTEM SHALL NOT refuse a discharge because the patient cannot pay; accepting the balance as due permits it.

Rationale
  Detaining a patient over a bill is prohibited by the Charter of Patients' Rights; the system records the debt instead.

FR-ENC-007 [P0]
A registrar must be able to cancel an encounter opened in error before any charge is posted.

Acceptance criteria
  IF a charge has been posted to the encounter THEN THE SYSTEM SHALL refuse cancellation.
  WHEN an encounter is cancelled THE SYSTEM SHALL keep it with its reason and exclude it from reports.

FR-ENC-008 [P0]
An encounter must be closed once every bill on it is settled and every claim on it is concluded.

Acceptance criteria
  WHEN the last open bill is settled and no claim remains open THE SYSTEM SHALL move the encounter to closed.
  WHILE an encounter is closed THE SYSTEM SHALL refuse new charges.

FR-ENC-009 [P1]
A registrar must be able to convert an OPD or emergency encounter into an admission, carrying its charges over.

Acceptance criteria
  WHEN an encounter is converted THE SYSTEM SHALL move its unbilled charges to the new IPD encounter and link the two.

FR-ENC-010 [P1]
A patient death during a stay must be recorded, and the encounter handled under the deceased-patient rules.

Acceptance criteria
  WHEN a death is recorded THE SYSTEM SHALL move the encounter to discharge initiated with reason death.
  THE SYSTEM SHALL NOT make release of the body conditional on payment.

## 11 Tariffs and packages

FR-TAR-001 [P0]
An administrator must be able to maintain a service catalogue in which each billable service has a code, a name, a department and a service class.

Acceptance criteria
  THE SYSTEM SHALL accept service classes consultation, room, procedure, investigation, pharmacy item, consumable, implant, package and other.
  IF a service code already exists in the tenant THEN THE SYSTEM SHALL refuse the duplicate.

FR-TAR-002 [P0]
Each service must carry its GST classification: SAC or HSN code, and whether it is exempt health care, taxable, or taxable room rent.

Acceptance criteria
  THE SYSTEM SHALL require a SAC or HSN code and a GST treatment for every service.
  WHERE a service is marked cosmetic THE SYSTEM SHALL treat it as taxable at the configured rate.

FR-TAR-003 [P0]
A price list must give a price for each service per room category, and be versioned with an effective date.

Acceptance criteria
  WHEN a price list version is published THE SYSTEM SHALL apply it to charges posted on or after its effective date.
  THE SYSTEM SHALL NOT change a published price list version; a change requires a new version.
  IF a service has no price in the applicable version for the room category THEN THE SYSTEM SHALL fall back to the version's base price for that service.

FR-TAR-004 [P0]
Each payer contract must name the price list that applies to its members.

Acceptance criteria
  WHEN a charge is posted to an encounter THE SYSTEM SHALL price it from the price list named by the encounter's payer contract.
  WHERE the encounter is cash THE SYSTEM SHALL use the tenant's cash price list.

FR-TAR-005 [P0]
An administrator must be able to define a package: a fixed price for a procedure that includes a defined set of services for a defined number of days.

Acceptance criteria
  THE SYSTEM SHALL record a package's price, included services with quantity limits, room category and length of stay.
  WHEN a service outside the package is posted to a package encounter THE SYSTEM SHALL bill it separately.
  WHEN an included service exceeds its quantity limit THE SYSTEM SHALL bill the excess separately.

FR-TAR-006 [P0]
Scheme packages must be priced from the scheme's own package master and adjustments.

Acceptance criteria
  WHEN a PM-JAY package is booked THE SYSTEM SHALL apply the state's package rate and the tenant's configured incentive multipliers.
  WHEN more than one surgical package is booked in one session THE SYSTEM SHALL apply the configured multi-procedure percentages.
  WHEN a CGHS rate is applied THE SYSTEM SHALL adjust it for the city tier, the NABH status and the ward entitlement from configuration.

FR-TAR-007 [P0]
Items under a government price ceiling must never be priced above the ceiling.

Acceptance criteria
  IF a price list gives an item a price above its configured ceiling price THEN THE SYSTEM SHALL refuse to publish the version.
  IF a charge would be posted above the ceiling THEN THE SYSTEM SHALL refuse it.

Rationale
  NPPA caps coronary stents and knee implants; scheduled formulations follow NLEM ceiling prices.

FR-TAR-008 [P0]
Room rent must be priced per day from the room category of each room period.

Acceptance criteria
  THE SYSTEM SHALL post one room-rent charge per day of stay, priced for the room category occupied at the configured day boundary.
  WHEN a room period changes category within a day THE SYSTEM SHALL charge the day at the category occupied at the day boundary.

FR-TAR-009 [P1]
A tenant must be able to publish its tariff for display to the public in English and the local language.

Acceptance criteria
  WHEN a price list version is published THE SYSTEM SHALL produce a display tariff in English and the facility's configured local language.
## 12 Charges

A charge line is one priced service posted to an encounter. The encounter's charge lines are its
account; bills are drawn from that account.

FR-CHG-001 [P0]
A billing executive must be able to post a charge for a service to an open encounter.

Acceptance criteria
  WHEN a charge is posted THE SYSTEM SHALL price it from the applicable price list version, room category and payer contract.
  THE SYSTEM SHALL record the service, quantity, unit price, ordering doctor, performing department and service date on the line.
  IF the encounter is not open, admitted or discharge initiated THEN THE SYSTEM SHALL refuse the charge.

FR-CHG-002 [P0]
Clinical systems must be able to post charges through an authenticated inbound interface.

Acceptance criteria
  WHEN a clinical system posts a charge with a valid facility credential THE SYSTEM SHALL post it as if a billing executive had.
  IF the same external reference is posted twice THEN THE SYSTEM SHALL keep the first and acknowledge the second without posting it.
  IF the service code is unknown THEN THE SYSTEM SHALL hold the charge in an exceptions queue.

FR-CHG-003 [P0]
Room rent must be posted automatically each day for every admitted encounter.

Acceptance criteria
  WHEN the configured day boundary passes THE SYSTEM SHALL post one room-rent charge for each admitted encounter, per FR-TAR-008.
  IF the room-rent posting for a day already exists THEN THE SYSTEM SHALL NOT post it again.

FR-CHG-004 [P0]
A posted charge must be corrected only by a reversal line, never by editing it.

Acceptance criteria
  WHEN a charge is reversed THE SYSTEM SHALL post a reversing line referencing the original with a recorded reason.
  THE SYSTEM SHALL NOT change the amount, quantity or service of a posted charge line.
  IF a charge is already on a final bill THEN THE SYSTEM SHALL refuse its reversal and require a credit note instead.

FR-CHG-005 [P0]
Doctor visit charges must carry the visiting doctor so that fee share can be computed.

Acceptance criteria
  WHEN a consultation or visit charge is posted THE SYSTEM SHALL require the doctor who performed it.

FR-CHG-006 [P0]
Charges for scheme beneficiaries must never be collectible from the beneficiary.

Acceptance criteria
  WHILE an encounter's financial class is scheme THE SYSTEM SHALL assign every charge line to the scheme payer.
  THE SYSTEM SHALL NOT assign a patient share to a line on a scheme encounter.

Rationale
  PM-JAY forbids any charge to the beneficiary; the package covers stay, drugs, diagnostics and fifteen days of post-discharge medicines.

FR-CHG-007 [P0]
Each charge line on an insured encounter must be classified against the payer's non-payable lists.

Acceptance criteria
  WHEN a charge is posted to an insured encounter THE SYSTEM SHALL mark it payable, non-payable or subsumed according to the payer's configured item lists.
  THE SYSTEM SHALL assign non-payable lines to the patient share.

FR-CHG-008 [P0]
Proportionate deduction for an insured encounter whose room category exceeds the policy's entitlement must be computed per the payer's rules.

Acceptance criteria
  WHERE the policy limits room rent THE SYSTEM SHALL compute the proportion of the entitled room rent to the actual room rent for each day.
  THE SYSTEM SHALL apply the proportion only to the service classes the payer's rules name as associated charges.
  THE SYSTEM SHALL NOT apply the proportion to pharmacy items, consumables, implants, medical devices, diagnostics or ICU charges.
  THE SYSTEM SHALL assign the deducted amount to the patient share.

## 13 Bills

FR-BIL-001 [P0]
A billing executive must be able to produce an interim bill for an admitted encounter at any time.

Acceptance criteria
  WHEN an interim bill is requested THE SYSTEM SHALL show every charge line posted so far with the patient and payer shares.
  THE SYSTEM SHALL NOT assign a document number to an interim bill.

FR-BIL-002 [P0]
A billing executive must be able to finalise a bill for an encounter, after which it cannot change.

Acceptance criteria
  WHEN a bill is finalised THE SYSTEM SHALL assign the next number from the facility's series and freeze its lines, amounts and taxes.
  THE SYSTEM SHALL NOT change a finalised bill.
  IF the encounter has a charge in the exceptions queue THEN THE SYSTEM SHALL refuse finalisation.

FR-BIL-003 [P0]
A final bill must separate the patient's share from each payer's share.

Acceptance criteria
  WHEN a bill is finalised THE SYSTEM SHALL issue one document to the patient for the patient share and one claim statement per payer.
  THE SYSTEM SHALL make the patient share and the payer shares add up to the bill total exactly.

FR-BIL-004 [P0]
A package bill must show the package, the charges it covers, and the charges billed beyond it.

Acceptance criteria
  WHEN a package encounter is billed THE SYSTEM SHALL show the package price as one line and every excluded or excess charge as its own line.
  THE SYSTEM SHALL show each covered charge with zero amount on the itemised annexure.

FR-BIL-005 [P0]
A billing executive must be able to apply a discount to a bill line or to the bill, within their limit or with approval.

Acceptance criteria
  WHEN a discount is applied THE SYSTEM SHALL record its reason and the member who gave it.
  IF the discount exceeds the member's limit THEN THE SYSTEM SHALL hold it for approval per FR-AUTHZ-005.
  THE SYSTEM SHALL NOT discount a payer's share without the payer contract permitting it.

FR-BIL-006 [P0]
A finalised bill must be corrected only by a credit note or debit note against it.

Acceptance criteria
  WHEN a credit note is issued THE SYSTEM SHALL number it from the credit-note series and reference the original bill.
  THE SYSTEM SHALL NOT let the credit notes against a bill exceed its total.

FR-BIL-007 [P0]
A finalised bill may be cancelled only before any payment or claim is applied to it, and only with approval.

Acceptance criteria
  IF a payment or claim has been applied to the bill THEN THE SYSTEM SHALL refuse cancellation.
  WHEN a bill is cancelled THE SYSTEM SHALL keep its number and mark it cancelled.

FR-BIL-008 [P0]
A billing executive must be able to give a patient a written estimate before admission or a procedure.

Acceptance criteria
  WHEN an estimate is issued THE SYSTEM SHALL price it from the price list the patient's expected payer would use.
  WHEN an estimate is issued THE SYSTEM SHALL record the expected length of stay and room category it assumes.
  WHEN the running charges of the encounter exceed the accepted estimate by the configured percentage THE SYSTEM SHALL notify the billing desk.

FR-BIL-009 [P0]
A patient's bill must be itemised on request.

Acceptance criteria
  WHEN an itemised bill is requested THE SYSTEM SHALL list every charge line with date, service, quantity, unit price and amount.

FR-BIL-010 [P0]
The patient document must carry the rounding adjustment as its own line.

Acceptance criteria
  THE SYSTEM SHALL round the payable amount to the rupee using the tenant's rounding rule and show the difference as a line.

## 14 GST and e-invoicing

FR-TAX-001 [P0]
Each bill line must be taxed according to its service's GST treatment on the service date.

Acceptance criteria
  THE SYSTEM SHALL treat health-care services by the facility as exempt.
  THE SYSTEM SHALL tax taxable lines at the rate effective on the line's service date.
  THE SYSTEM SHALL keep rate history so that a bill is always taxed at the rates in force on each line's service date.

FR-TAX-002 [P0]
Room rent above the configured daily threshold in a non-intensive-care room category must be taxed at the configured rate.

Acceptance criteria
  WHEN a room-rent line for a non-ICU category exceeds the configured daily threshold THE SYSTEM SHALL tax it at the configured room-rent rate.
  THE SYSTEM SHALL NOT tax room rent in an ICU, CCU, ICCU or NICU category.

FR-TAX-003 [P0]
Pharmacy items, consumables and implants supplied to an in-patient must be treated as part of the exempt health-care supply.

Acceptance criteria
  WHILE the encounter is IPD or day care THE SYSTEM SHALL treat pharmacy items, consumables and implants on it as exempt.

FR-TAX-004 [P0]
A bill's document type must follow its taxability.

Acceptance criteria
  IF every line is exempt THEN THE SYSTEM SHALL issue a bill of supply.
  IF every line is taxable THEN THE SYSTEM SHALL issue a tax invoice.
  IF the bill mixes exempt and taxable lines THEN THE SYSTEM SHALL issue an invoice-cum-bill of supply.

FR-TAX-005 [P0]
A tax invoice must show the GST split into central and state tax for intra-state supply, or integrated tax for inter-state supply.

Acceptance criteria
  WHEN the place of supply is in the facility's state THE SYSTEM SHALL split tax equally into CGST and SGST.
  WHEN the place of supply is in another state THE SYSTEM SHALL charge IGST.

FR-TAX-006 [P0]
Where a tenant is obliged to register e-invoices, business-to-business taxable invoices must be registered with the IRP.

Acceptance criteria
  WHEN a taxable invoice to a GST-registered recipient is finalised by an obliged tenant THE SYSTEM SHALL submit it to the IRP.
  WHEN the IRP returns an IRN THE SYSTEM SHALL print the IRN and signed QR code on the invoice.
  IF submission fails THEN THE SYSTEM SHALL retry and alert the finance manager when the reporting window has fewer than two days left.

FR-TAX-007 [P1]
Where a tenant is obliged to print a dynamic QR code, taxable consumer invoices must carry it.

Acceptance criteria
  WHERE the tenant has the dynamic-QR obligation THE SYSTEM SHALL print a dynamic payment QR code on each taxable invoice to an unregistered recipient.

FR-TAX-008 [P0]
The finance manager must be able to produce the GST return data for a period.

Acceptance criteria
  WHEN a GST summary is requested for a month THE SYSTEM SHALL total taxable value, exempt value and tax by rate, by GSTIN, and by document type.
  THE SYSTEM SHALL include credit and debit notes in the period they were issued.

FR-TAX-009 [P0]
A tax invoice to an unregistered recipient whose taxable value is Rs 50,000 or more must carry the recipient's name, address and state.

Acceptance criteria
  IF the recipient's name, address or state is missing on such an invoice THEN THE SYSTEM SHALL refuse finalisation.

FR-TAX-010 [P0]
Pharmacy items sold to an out-patient must be taxed at their HSN rate.

Acceptance criteria
  WHILE the encounter is OPD THE SYSTEM SHALL tax pharmacy items on it at their HSN rate.
## 15 Payments, deposits and refunds

FR-PAY-001 [P0]
A cashier must be able to take a deposit against an encounter and issue a receipt.

Acceptance criteria
  WHEN a deposit is taken THE SYSTEM SHALL issue a numbered advance receipt linked to the encounter.
  THE SYSTEM SHALL hold the deposit as an unapplied credit of the encounter until a bill is settled.

FR-PAY-002 [P0]
A cashier must be able to collect a payment against a bill's patient share.

Acceptance criteria
  WHEN a payment is collected THE SYSTEM SHALL issue a numbered receipt and reduce the bill's outstanding patient share.
  IF the payment exceeds the outstanding patient share THEN THE SYSTEM SHALL refuse it and offer to record the excess as a deposit.

FR-PAY-003 [P0]
Deposits held for an encounter must be applied to its final bill's patient share when the bill is finalised.

Acceptance criteria
  WHEN a final bill is finalised THE SYSTEM SHALL apply the encounter's unapplied deposits to the patient share, oldest first.
  WHEN the deposits exceed the patient share THE SYSTEM SHALL record the excess as refundable.

FR-PAY-004 [P0]
Payment modes must include cash, card, UPI, bank transfer and cheque.

Acceptance criteria
  THE SYSTEM SHALL record the mode and the mode's reference for every receipt.
  WHERE the mode is card or UPI through the gateway THE SYSTEM SHALL record the receipt only when the gateway confirms the payment.

FR-PAY-005 [P0]
Cash received from one person must be refused at or above the legal limit per day, per transaction and per event.

Acceptance criteria
  IF a cash receipt would bring the cash received from the payer for the encounter to the configured limit or above THEN THE SYSTEM SHALL refuse it.
  IF a cash receipt would bring the cash received from the payer in a day to the configured limit or above THEN THE SYSTEM SHALL refuse it.

Rationale
  Income-tax law forbids receiving Rs 2 lakh or more in cash from one person for one event; an admission is one event.

FR-PAY-006 [P0]
A receipt of a configured amount or more must record the payer's PAN or a declaration in its place.

Acceptance criteria
  IF a receipt reaches the configured amount and neither a PAN nor a declaration is recorded THEN THE SYSTEM SHALL refuse it.

FR-PAY-007 [P0]
Card and UPI payments must be collectable through the payment gateway with confirmation received asynchronously.

Acceptance criteria
  WHEN the gateway confirms a payment THE SYSTEM SHALL issue the receipt once, even if the confirmation arrives more than once.
  IF a confirmation arrives for an amount different from the request THEN THE SYSTEM SHALL hold it for review and not issue a receipt.
  WHEN a payment request has had no confirmation for the configured period THE SYSTEM SHALL query the gateway for its status.

FR-PAY-008 [P0]
A refund of an encounter's refundable balance must be requested, approved and paid.

Acceptance criteria
  WHEN a refund is requested THE SYSTEM SHALL require the amount, mode and payee.
  THE SYSTEM SHALL NOT pay a refund before it is approved per FR-AUTHZ-005.
  IF the amount exceeds the encounter's refundable balance THEN THE SYSTEM SHALL refuse the request.
  WHEN a refund is paid THE SYSTEM SHALL issue a refund voucher and reduce the refundable balance.

FR-PAY-009 [P0]
Refunds of payments made by card or UPI must go back to the original instrument through the gateway where the gateway permits it.

Acceptance criteria
  WHERE the original payment was through the gateway and within the gateway's refund window THE SYSTEM SHALL refund to the original instrument.

FR-PAY-010 [P0]
A receipt must be cancelled only by the issuing cashier within their open shift, or by approval afterwards.

Acceptance criteria
  WHEN a receipt is cancelled THE SYSTEM SHALL keep its number, mark it cancelled and restore the bill's outstanding amount.
  IF the receipt's shift is closed THEN THE SYSTEM SHALL require approval to cancel it.

FR-PAY-011 [P0]
A cashier must work within a shift that is opened with a float and closed with a count.

Acceptance criteria
  IF a cashier has no open shift THEN THE SYSTEM SHALL refuse to issue a receipt.
  WHEN a shift is opened THE SYSTEM SHALL record the opening float.
  WHEN a shift is closed THE SYSTEM SHALL record the counted cash by denomination and compute the variance against the expected cash.

FR-PAY-012 [P0]
A shift closed with a variance must be reconciled by a finance manager with an explanation.

Acceptance criteria
  IF a closed shift has a non-zero variance THEN THE SYSTEM SHALL keep it in closed until a finance manager records an explanation.
  WHEN the explanation is recorded THE SYSTEM SHALL move the shift to reconciled.

FR-PAY-013 [P1]
A cashier must be able to hand over a shift to another cashier without closing the facility's counter.

Acceptance criteria
  WHEN a shift is handed over THE SYSTEM SHALL close the outgoing shift with a count and open the incoming shift with the counted cash as its float.

## 16 Payers and contracts

FR-PYR-001 [P0]
An administrator must be able to register a payer as an insurer, a TPA, a government scheme or a corporate.

Acceptance criteria
  THE SYSTEM SHALL record a payer's type, name and claim channel.
  WHEN a TPA is registered THE SYSTEM SHALL require the insurers it acts for.

FR-PYR-002 [P0]
An administrator must be able to record a payer contract with its price list, validity period and settlement terms.

Acceptance criteria
  WHEN a contract is activated THE SYSTEM SHALL apply it to encounters opened within its validity period.
  IF two active contracts for the same payer and facility overlap in validity THEN THE SYSTEM SHALL refuse the activation.

FR-PYR-003 [P0]
A payer contract must carry the payer's item lists: non-payable, subsumed into room, subsumed into procedure and subsumed into treatment.

Acceptance criteria
  THE SYSTEM SHALL let an administrator map each service to at most one of the payer's item lists.
  WHERE no mapping exists for a service THE SYSTEM SHALL treat it as payable.

FR-PYR-004 [P0]
A payer contract must carry the payer's deadlines: pre-authorisation decision, discharge authorisation, and claim submission.

Acceptance criteria
  THE SYSTEM SHALL default an insurer contract's deadlines to the configured regulatory values.
  THE SYSTEM SHALL default a scheme contract's claim-submission window to the scheme's configured value.

FR-PYR-005 [P1]
A corporate payer contract must record the credit limit per employee and the approval letter required.

Acceptance criteria
  IF a corporate encounter's payer share would exceed the employee's credit limit THEN THE SYSTEM SHALL assign the excess to the patient share.

## 17 Pre-authorisation and claims

FR-CLM-001 [P0]
An insurance executive must be able to prepare a pre-authorisation request for an insured or scheme encounter.

Acceptance criteria
  WHEN a pre-authorisation is prepared THE SYSTEM SHALL fill it from the encounter, the entitlement, the admitting diagnosis and the estimate.
  THE SYSTEM SHALL require the documents the payer's contract lists for pre-authorisation.

FR-CLM-002 [P0]
Submission of a pre-authorisation must start the payer's decision clock.

Acceptance criteria
  WHEN a pre-authorisation is submitted THE SYSTEM SHALL record the submission time and the payer's decision deadline.
  WHEN the deadline is within the configured warning period and no decision is recorded THE SYSTEM SHALL alert the insurance desk.
  WHEN the deadline passes with no decision THE SYSTEM SHALL mark the case breached by the payer.

FR-CLM-003 [P0]
An insurance executive must be able to record a payer's decision on a pre-authorisation.

Acceptance criteria
  THE SYSTEM SHALL accept the decisions approved, partially approved, query and denied.
  WHEN a pre-authorisation is approved THE SYSTEM SHALL record the approved amount and the approval reference.
  WHEN a query is raised THE SYSTEM SHALL pause the payer's clock until the query is answered.

FR-CLM-004 [P0]
An insurance executive must be able to request an enhancement when running charges approach the approved amount.

Acceptance criteria
  WHEN the running payer share of an encounter reaches the configured percentage of the approved amount THE SYSTEM SHALL alert the insurance desk.
  WHEN an enhancement is submitted THE SYSTEM SHALL start a new decision clock.

FR-CLM-005 [P0]
A denied or partially approved pre-authorisation must move the unapproved amount to the patient share.

Acceptance criteria
  WHEN a pre-authorisation is denied THE SYSTEM SHALL change the encounter's financial class to cash unless the patient chooses another entitlement.
  WHEN a pre-authorisation is partially approved THE SYSTEM SHALL cap the payer share at the approved amount.

FR-CLM-006 [P0]
A scheme pre-authorisation must be booked against a scheme package.

Acceptance criteria
  THE SYSTEM SHALL require a package from the scheme's package master on a scheme pre-authorisation.
  WHEN a scheme pre-authorisation is approved THE SYSTEM SHALL set the encounter's package.

FR-CLM-007 [P0]
An insurance executive must be able to prepare a claim for an encounter once its final bill is issued.

Acceptance criteria
  WHEN a claim is prepared THE SYSTEM SHALL fill it from the final bill's payer statement and the approved pre-authorisation.
  THE SYSTEM SHALL require the documents the payer's contract lists for claims.

FR-CLM-008 [P0]
Claim submission must be recorded with the channel used and must respect the payer's submission window.

Acceptance criteria
  WHEN a claim is submitted THE SYSTEM SHALL record the channel, the submission time and the payer's reference.
  WHEN the submission window is within the configured warning period and the claim is unsubmitted THE SYSTEM SHALL alert the insurance desk.
  IF the window has passed THEN THE SYSTEM SHALL require a condonation reason to submit.

FR-CLM-009 [P0]
Discharge authorisation for a cashless encounter must be requested and tracked against the payer's deadline.

Acceptance criteria
  WHEN a discharge is initiated on a cashless encounter THE SYSTEM SHALL require a discharge-authorisation request with the interim bill.
  WHEN the discharge-authorisation deadline passes with no decision THE SYSTEM SHALL mark the case breached by the payer and record the time.
  WHEN the payer is recorded as having breached THE SYSTEM SHALL tag any room charge accrued after the deadline as recoverable from the payer.

Rationale
  Under the IRDAI master circular, charges caused by a delay beyond three hours are borne by the insurer.

FR-CLM-010 [P0]
An insurance executive must be able to record a payer query on a claim and its answer.

Acceptance criteria
  WHEN a claim query is recorded THE SYSTEM SHALL move the claim to query raised and record the query deadline.
  WHEN the answer is submitted THE SYSTEM SHALL move the claim back to submitted.

FR-CLM-011 [P0]
A claim settlement must be recorded with the amount paid, the deductions by reason, and the payment reference.

Acceptance criteria
  WHEN a settlement is recorded THE SYSTEM SHALL require every deduction to carry a reason from the configured deduction reasons.
  THE SYSTEM SHALL make the amount paid plus the deductions equal the claimed amount.
  WHEN a settlement is recorded THE SYSTEM SHALL reduce the payer's receivable by the amount paid.

FR-CLM-012 [P0]
Claim deductions must be routed to recovery from the patient, dispute with the payer, or write-off.

Acceptance criteria
  WHEN a deduction is routed to the patient THE SYSTEM SHALL raise a debit note to the patient.
  THE SYSTEM SHALL NOT route a deduction on a scheme encounter to the patient.
  WHEN a deduction is written off THE SYSTEM SHALL require approval per FR-AUTHZ-005.

FR-CLM-013 [P1]
Claims to payers on NHCX must be submitted and tracked through NHCX.

Acceptance criteria
  WHERE the payer's claim channel is NHCX THE SYSTEM SHALL submit the pre-authorisation and claim through NHCX.
  WHEN NHCX delivers a payer response THE SYSTEM SHALL record it as the payer's decision.

FR-CLM-014 [P0]
A submitted claim that the payer has not settled within the contract's settlement terms must be marked overdue.

Acceptance criteria
  WHEN a submitted claim passes the contract's settlement period without a settlement THE SYSTEM SHALL mark it overdue and alert the insurance desk.
## 18 Doctor fee share and TDS

Visiting consultants are paid a share of the fees billed for their services. Salaried doctors
are out of scope.

FR-FEE-001 [P0]
An administrator must be able to record a fee-share rule per doctor and service class, as a percentage or a fixed amount.

Acceptance criteria
  THE SYSTEM SHALL record each rule with its effective date.
  IF two rules for one doctor and service class have overlapping effective periods THEN THE SYSTEM SHALL refuse the second.

FR-FEE-002 [P0]
A doctor's fee share must accrue when the bill carrying the doctor's charge is finalised.

Acceptance criteria
  WHEN a bill is finalised THE SYSTEM SHALL accrue the fee share for each line that names a fee-share doctor.
  WHEN a credit note reduces such a line THE SYSTEM SHALL reverse the matching accrual.

FR-FEE-003 [P0]
Fee share on the payer's portion must be payable only after the payer settles, in proportion to the amount settled.

Acceptance criteria
  WHEN a claim settles THE SYSTEM SHALL release the fee share on the settled portion of each line.
  THE SYSTEM SHALL NOT release fee share on an amount the payer deducted.

FR-FEE-004 [P0]
A finance manager must be able to run a monthly fee payout per doctor, deducting TDS.

Acceptance criteria
  WHEN a payout is run THE SYSTEM SHALL total the released fee share per doctor for the period.
  WHEN a doctor's payments in the financial year cross the configured threshold THE SYSTEM SHALL deduct TDS at the configured rate on that payout and later ones.
  IF a doctor has no PAN recorded THEN THE SYSTEM SHALL deduct TDS at the configured no-PAN rate.

FR-FEE-005 [P1]
The finance manager must be able to export the TDS deducted for the quarterly return.

Acceptance criteria
  WHEN a TDS export is requested for a quarter THE SYSTEM SHALL list each deduction with payee PAN, amount paid, TDS and the configured section code.

## 19 Receivables and accounting export

FR-AR-001 [P0]
Every amount owed to the hospital must be held as a receivable against the patient or the payer who owes it.

Acceptance criteria
  WHEN a bill is finalised THE SYSTEM SHALL create a receivable for the patient share and one for each payer share.
  WHEN a receipt, settlement, credit note or write-off is recorded THE SYSTEM SHALL reduce the matching receivable.

FR-AR-002 [P0]
A finance manager must be able to see receivables aged by due date, by payer.

Acceptance criteria
  WHEN the ageing report is requested THE SYSTEM SHALL bucket each receivable as 0-30, 31-60, 61-90, 91-180 and over 180 days.

FR-AR-003 [P0]
A finance manager must be able to write off a receivable with approval.

Acceptance criteria
  WHEN a write-off is approved THE SYSTEM SHALL reduce the receivable and record the reason.

FR-AR-004 [P0]
Every financial document must produce balanced ledger postings.

Acceptance criteria
  WHEN a bill, receipt, refund, credit note, debit note, settlement, write-off or fee payout is recorded THE SYSTEM SHALL post ledger entries whose debits equal their credits.
  THE SYSTEM SHALL NOT change a ledger entry after posting; a correction is a new entry.

FR-AR-005 [P1]
A finance manager must be able to export ledger postings for a period as a voucher file for the accounting system.

Acceptance criteria
  WHEN an export is run THE SYSTEM SHALL include every posting in the period exactly once across exports.
  WHEN an export is run THE SYSTEM SHALL map each ledger account to the tenant's configured accounting ledger name.

FR-AR-006 [P0]
Payer bank settlements must be matched to claims.

Acceptance criteria
  WHEN a finance manager records a bank credit from a payer THE SYSTEM SHALL propose the claims it settles by amount and reference.
  IF the matched settlements do not add up to the credit THEN THE SYSTEM SHALL keep the unmatched remainder as an unapplied payer credit.

## 20 Notifications

FR-NOT-001 [P0]
All messages must go through one notification service supporting SMS, WhatsApp and email.

Acceptance criteria
  THE SYSTEM SHALL send every message listed in Appendix C through the notification service.
  THE SYSTEM SHALL record every message per recipient per channel with its delivery state.

FR-NOT-002 [P0]
Every SMS must use a template registered on the DLT platform.

Acceptance criteria
  IF a message's SMS template has no registered DLT template identifier THEN THE SYSTEM SHALL NOT send the SMS.
  THE SYSTEM SHALL send the tenant's registered sender header with each SMS.

FR-NOT-003 [P0]
Delivery must be asynchronous and must never block or fail the action that caused it.

Acceptance criteria
  IF a channel fails THEN THE SYSTEM SHALL complete the originating action and retry the message.
  THE SYSTEM SHALL NOT send the same message to the same recipient on the same channel twice.

FR-NOT-004 [P0]
Patients must receive documents by a link that expires, not as attachments carrying the full document on an unauthenticated channel.

Acceptance criteria
  WHEN a bill, receipt or estimate is sent THE SYSTEM SHALL send a link valid for the configured period.
  WHEN the link is opened THE SYSTEM SHALL require the patient's mobile number to be confirmed by a one-time code.

FR-NOT-005 [P1]
A patient must be able to opt out of non-transactional messages.

Acceptance criteria
  WHEN a patient opts out THE SYSTEM SHALL stop non-transactional messages to them on every channel.
  THE SYSTEM SHALL keep sending transactional messages after an opt-out.

FR-NOT-006 [P0]
Staff alerts must be delivered in the application and by email.

Acceptance criteria
  WHEN a staff alert in Appendix C is raised THE SYSTEM SHALL show it in the application to every member holding the named role at the facility.
## 21 Audit and data protection

FR-AUD-001 [P0]
Every change to a financial document, a price, a tariff, a payer contract, a permission or a patient's personal data must be recorded in an append-only audit log.

Acceptance criteria
  WHEN any such change is made THE SYSTEM SHALL record the actor, the tenant, the facility, the record, the action, the before and after values, the time and the source address.
  THE SYSTEM SHALL NOT provide any application path that changes or deletes an audit entry, including for platform operators.

Rationale
  This rule applies to every domain in this document. Finance, tax authorities and the Data Protection Board all ask the same question: who changed this, and when.

FR-AUD-002 [P0]
Every view of a patient's record by a staff member must be logged.

Acceptance criteria
  WHEN a staff member opens a patient's record, bill or claim THE SYSTEM SHALL log the member, the patient and the time.
  THE SYSTEM SHALL keep access logs for at least the configured log-retention period.

FR-AUD-003 [P0]
An administrator must be able to search the audit log by actor, record, action and period.

Acceptance criteria
  WHEN an administrator searches THE SYSTEM SHALL return only the tenant's own entries.

FR-AUD-004 [P0]
Records must be retained for the longest period any applicable law requires, per record class.

Acceptance criteria
  THE SYSTEM SHALL keep a retention period per record class in configuration.
  THE SYSTEM SHALL NOT erase a record before its class's retention period ends, including on a patient's request for erasure.

FR-AUD-005 [P1]
A patient's request to see or correct their personal data must be recorded and fulfilled.

Acceptance criteria
  WHEN a data request is recorded THE SYSTEM SHALL record its type, the date and the deadline.
  WHEN a correction is fulfilled THE SYSTEM SHALL record the before and after values in the audit log.

FR-AUD-006 [P0]
A suspected personal-data breach must be recorded and escalated within the regulatory timelines.

Acceptance criteria
  WHEN a breach is recorded THE SYSTEM SHALL notify the tenant's data-protection contact and the platform operator.
  WHEN a breach is recorded THE SYSTEM SHALL record the deadline for the detailed report to the Board from configuration.

## 22 Platform operations

FR-OPS-001 [P0]
A platform operator must be able to see each tenant's status, usage and last activity without seeing its patients' data.

Acceptance criteria
  THE SYSTEM SHALL show platform operators tenant-level counts and status only.
  THE SYSTEM SHALL NOT show a platform operator any patient's personal data outside support access under FR-AUTHZ-007.

FR-OPS-002 [P0]
A platform operator must be able to switch a feature on or off per tenant.

Acceptance criteria
  WHEN a feature flag changes THE SYSTEM SHALL apply it to the tenant's next request.

FR-OPS-003 [P0]
Scheduled jobs must run per tenant so that a failure for one tenant does not stop the others.

Acceptance criteria
  IF a scheduled job fails for one tenant THEN THE SYSTEM SHALL run it for the remaining tenants and alert the platform operator.

FR-OPS-004 [P1]
A platform operator must be able to announce planned maintenance to every tenant.

Acceptance criteria
  WHEN maintenance is scheduled THE SYSTEM SHALL show the notice to every signed-in member from the configured lead time.

## 23 Reports

FR-RPT-001 [P0]
A finance manager must be able to see the day's collections by facility, cashier and mode.

Acceptance criteria
  WHEN the collection report is requested THE SYSTEM SHALL total receipts net of cancellations and refunds by facility, cashier and mode for the day.

FR-RPT-002 [P0]
A finance manager must be able to see revenue by department and doctor for a period.

Acceptance criteria
  WHEN the revenue report is requested THE SYSTEM SHALL total finalised bill lines net of credit notes by department and by doctor.

FR-RPT-003 [P0]
The insurance desk must be able to see open cases by deadline.

Acceptance criteria
  WHEN the insurance desk opens its work list THE SYSTEM SHALL list open pre-authorisations, discharge authorisations and claims ordered by time to deadline.

FR-RPT-004 [P1]
A finance manager must be able to see payer deductions by payer and reason for a period.

Acceptance criteria
  WHEN the deduction report is requested THE SYSTEM SHALL total deductions by payer and reason.

FR-RPT-005 [P0]
A billing executive must be able to see admitted patients whose running charges exceed their deposits or approved amounts.

Acceptance criteria
  WHEN the exposure list is requested THE SYSTEM SHALL list each admitted encounter whose unsecured amount exceeds the configured threshold.

# Part IV — Non-functional requirements

NFR-001 [P0]
Tenant isolation must be verified by an automated test that attempts cross-tenant access through every route.

Acceptance criteria
  THE SYSTEM SHALL fail the build if any route returns another tenant's record to the isolation test.

NFR-002 [P0]
Monetary amounts must be stored and computed exactly, without floating-point arithmetic.

Acceptance criteria
  THE SYSTEM SHALL store amounts as integer paise.
  THE SYSTEM SHALL compute tax per line and round per the tenant's rounding rule.

NFR-003 [P0]
Document numbers in a series must be gapless and never reused.

Acceptance criteria
  WHEN two documents are finalised concurrently in one series THE SYSTEM SHALL give them consecutive distinct numbers.
  IF a transaction that took a number fails THEN THE SYSTEM SHALL NOT leave a gap in the series.

NFR-004 [P0]
Finalising a bill of up to 2,000 lines must complete within 5 seconds at the 95th percentile.

Acceptance criteria
  THE SYSTEM SHALL finalise a 2,000-line bill within 5 seconds at the 95th percentile under the reference load.

NFR-005 [P0]
The service must be available 99.5% of each month, excluding announced maintenance.

Acceptance criteria
  THE SYSTEM SHALL report monthly availability per tenant.

NFR-006 [P0]
Data must be stored in India.

Acceptance criteria
  THE SYSTEM SHALL store every tenant's data, backups and logs in data centres located in India.

NFR-007 [P0]
Personal data and identity documents must be encrypted at rest and in transit.

Acceptance criteria
  THE SYSTEM SHALL refuse connections that do not use TLS 1.2 or later.
  THE SYSTEM SHALL encrypt the database and backups at rest with managed keys.

NFR-008 [P0]
Backups must allow restoring any tenant to a point within the last 7 days with at most 15 minutes of data loss.

Acceptance criteria
  THE SYSTEM SHALL restore a tenant to a chosen point within the last 7 days in a quarterly restore test.
  THE SYSTEM SHALL lose at most 15 minutes of committed data in that test.

NFR-009 [P0]
Personal data must not appear in application logs or error reports.

Acceptance criteria
  THE SYSTEM SHALL redact patient names, mobile numbers and identity numbers in the logging layer.

NFR-010 [P0]
The interface must be usable in English and Hindi, with every printed document supporting the facility's local language.

Acceptance criteria
  THE SYSTEM SHALL externalise every interface string for translation.
  THE SYSTEM SHALL render Devanagari on printed bills and receipts.

NFR-011 [P0]
Every inbound interface and webhook must be authenticated and idempotent.

Acceptance criteria
  IF an inbound request's signature or credential is invalid THEN THE SYSTEM SHALL reject it.
  WHEN a request with an idempotency key already processed arrives THE SYSTEM SHALL return the original result.

NFR-012 [P0]
Rate limiting must apply to sign-in, password reset, document links and every inbound interface.

Acceptance criteria
  IF a client exceeds the configured rate for an endpoint THEN THE SYSTEM SHALL refuse further requests for the configured period.

NFR-013 [P1]
The software must be able to be certified for ABDM milestones M1 and M2.

Acceptance criteria
  THE SYSTEM SHALL implement ABHA verification and care-context linking against the current ABDM API version.
# Part V — Decisions and questions

## 24 Design decisions

D-01 Tenancy model
Decision: One shared database. Every business table carries the tenant, and every query is scoped to it automatically.
Context: Target tenants are small hospitals; hundreds of tenants must run on one deployment.
Consequences: Isolation depends on the scoping never being bypassed, so NFR-001 tests every route. A large tenant can later be moved to its own database without a model change.
Rejected: A database per tenant. It gives stronger isolation but multiplies migrations, backups and monitoring by the tenant count, which the target price cannot carry.

D-02 Charges are the account; bills are drawn from it
Decision: An encounter's charge lines are the source of truth. A bill is a finalised, numbered snapshot drawn from them.
Context: In-patient stays accumulate charges for days; payers, packages and discounts change the split, not the charges.
Consequences: Interim bills cost nothing. Re-pricing after a payer change is a recomputation over open lines.
Rejected: A bill as an editable cart. It makes the interim bill a second source of truth and loses the history of what was charged when.

D-03 Finalised documents are immutable
Decision: A finalised bill, receipt, credit note, refund voucher or ledger entry is never edited. Corrections are new documents that reference the original.
Context: GST law, auditors and payers all rely on a document number meaning one fixed content.
Consequences: Every correction path needs its own document type and number series.
Rejected: Editable documents with an audit trail. An audit trail shows the change was made; it does not make the change lawful.

D-04 Patient and payer shares are computed per line at finalisation
Decision: Each bill line is split into patient and payer shares by the payer contract's rules when the bill is finalised; running shares are shown on interim bills.
Context: Non-payables, proportionate deduction, caps and packages all act per line.
Consequences: One bill yields one patient document and one statement per payer.
Rejected: Separate bills per payer from admission. The split is not known until the payer decides, and a patient would receive several bills for one stay.

D-05 Clinical systems are outside
Decision: Orders, pharmacy and laboratory stay in the hospital's clinical systems. Aarogya receives charges through the inbound interface of FR-CHG-002.
Context: Every target hospital already runs some clinical software, and replacing it is a different sale.
Consequences: Charges can arrive late or with unknown codes, hence the exceptions queue.
Rejected: A built-in order module. It doubles the product's scope before billing is proven.

D-06 Claims channels are adapters
Decision: A claim is prepared once and submitted through the payer's channel. v1 records manual portal submissions; NHCX is the first automated channel.
Context: NHCX is voluntary as of 2026, and each TPA portal differs.
Consequences: The claim record holds the channel and the payer's reference, not portal-specific fields.
Rejected: Integrating each TPA portal. It is brittle and the work is repeated per payer.

D-07 Deadlines belong to the payer contract
Decision: Pre-authorisation, discharge-authorisation and submission deadlines are carried on each payer contract, defaulted from regulatory configuration.
Context: IRDAI sets insurer deadlines; schemes set their own; corporates negotiate theirs.
Consequences: Changing a regulatory default changes new contracts only.
Rejected: Global constants. Scheme and corporate deadlines differ from the insurer rule.

D-08 Discharge does not wait for payment
Decision: Discharge requires the balance to be settled or accepted as due, never paid.
Context: Detaining a patient or body over a bill is prohibited.
Consequences: Receivables include patient balances accepted at discharge.
Rejected: Blocking discharge until paid.

D-09 Amounts in paise, rounding at the document
Decision: Amounts are integer paise. Tax is computed per line; the payable total is rounded to the rupee at the document, shown as its own line.
Context: GST is computed per line; patients pay whole rupees.
Consequences: Totals reconcile exactly.
Rejected: Decimal rupees with rounding per line. It makes the document total drift from the sum of lines.

## 25 Working assumptions

Every value below is a placeholder that becomes a configuration default.

| Parameter | Placeholder | Why it matters |
|---|---|---|
| room_rent_gst_threshold_per_day | Rs 5,000 | FR-TAX-002 |
| room_rent_gst_rate | 5% | FR-TAX-002 |
| icu_room_categories | ICU, CCU, ICCU, NICU | FR-TAX-002 |
| einvoice_turnover_threshold | Rs 5 crore | FR-TEN-005, FR-TAX-006 |
| einvoice_reporting_window_days | 30 | FR-TAX-006 |
| dynamic_qr_turnover_threshold | Rs 500 crore | FR-TAX-007 |
| unregistered_recipient_detail_threshold | Rs 50,000 | FR-TAX-009 |
| cash_receipt_limit | Rs 2,00,000 | FR-PAY-005 |
| pan_required_amount | Rs 2,00,000 | FR-PAY-006 |
| preauth_decision_hours | 1 | FR-PYR-004, FR-CLM-002 |
| discharge_auth_hours | 3 | FR-CLM-009 |
| deadline_warning_minutes | 20 | FR-CLM-002, FR-CLM-008 |
| enhancement_alert_percent | 80% | FR-CLM-004 |
| scheme_claim_window_days | 15 | FR-PYR-004 |
| claim_settlement_days | 30 | FR-CLM-014 |
| estimate_overrun_percent | 20% | FR-BIL-008 |
| pmjay_multi_procedure_percent | 100, 50, 25 | FR-TAR-006 |
| cghs_city_tier_adjustment | 0, -10%, -20% | FR-TAR-006 |
| cghs_ward_adjustment | general -5%, semi-private 0, private +5% | FR-TAR-006 |
| room_day_boundary | 00:00 | FR-TAR-008, FR-CHG-003 |
| tds_threshold_per_year | Rs 50,000 | FR-FEE-004 |
| tds_rate | 10% | FR-FEE-004 |
| tds_rate_without_pan | 20% | FR-FEE-004 |
| tds_section_code | 393(1) Table 6(iii).D | FR-FEE-005 |
| document_link_valid_hours | 72 | FR-NOT-004 |
| session_idle_minutes | 30 | FR-ACC-008 |
| duplicate_match_threshold | 0.85 | FR-PAT-002 |
| log_retention_days | 365 | FR-AUD-002 |
| breach_report_hours | 72 | FR-AUD-006 |
| retention_years_medical_financial | 8 | FR-AUD-004 |
| exposure_threshold | Rs 10,000 | FR-RPT-005 |
| gateway_status_poll_minutes | 15 | FR-PAY-007 |

## 26 Open questions

| Id | Question | Owner | Blocks |
|---|---|---|---|
| OQ-01 | Is the SaaS vendor a data processor only, or also a fiduciary for platform-operator data? The contract template depends on it. | Legal | FR-AUD-006, FR-OPS-001 |
| OQ-02 | Which states' scheme package masters ship at launch beyond PM-JAY and CGHS? | Product | FR-TAR-006 (parameter) |
| OQ-03 | Are in-patient pharmacy items exempt as part of a composite supply in every state we sell into? The position rests on advance rulings. | Legal (tax) | FR-TAX-003 (shape: may need a per-tenant override) |
| OQ-04 | Does a room category change within a day charge the day at the higher category or at the category at the day boundary? | Hospital finance lead | FR-TAR-008 (parameter) |
| OQ-05 | Is a debit note to the patient for a claim deduction acceptable to hospitals, or do they prefer a fresh bill? | Hospital finance lead | FR-CLM-012 (shape) |
| OQ-06 | Which accounting system's voucher format ships first? | Product | FR-AR-005 (parameter) |
| OQ-07 | Who in a tenant receives breach notifications when no data-protection contact is named? | Legal | FR-AUD-006 (parameter) |

# Part VI — Delivery

## 27 Phase plan

Every phase before phase 5 builds server-side behaviour only. Phase 5 publishes the API
contract; phase 6 builds the screens against it.

| Phase | Name | Domains | Exit gate |
|---|---|---|---|
| 0 | Foundations | TEN, ACC, AUTHZ, AUD, NOT, OPS, NFR | Two tenants provisioned; members act only within their facility roles; the isolation test passes on every route; an audit entry and a notification are produced end to end |
| 1 | Patients, encounters, tariffs and payers | PAT, ENC, TAR, PYR | A patient registered, admitted with a payer, moved between room categories, with every service priced from the right price list |
| 2 | Charges, bills and GST | CHG, BIL, TAX | A mixed exempt and taxable in-patient bill finalised with correct document type, tax and number |
| 3 | Money | PAY, AR | Deposit, payment, refund and a shift reconciled; ledger postings balance |
| 4 | Claims, fees and reports | CLM, FEE, RPT | A cashless case from pre-authorisation to settlement with deductions; a fee payout with TDS |
| 5 | API contract | none | OpenAPI published; every journey step reachable |
| 6 | Screens | none | Every journey walkable end to end in a browser |
# Appendices

## Appendix A — Glossary

| Term | Meaning |
|---|---|
| Tenant | One hospital business on the platform; the unit of data isolation |
| Facility | A hospital, clinic or day-care centre of a tenant, under one GSTIN |
| Member | A staff account's membership of one tenant |
| UHID | Unique hospital identifier of a patient within a tenant |
| Encounter | One episode of care billed as a unit: OPD visit, IPD admission, day care or emergency |
| Room period | A span of an in-patient stay in one room category |
| Financial class | How an encounter is paid: cash, insured, scheme or corporate |
| Entitlement | A patient's right to have a payer pay: a policy, a scheme card or an employer letter |
| Payer | An insurer, a TPA, a government scheme or a corporate that pays for care |
| Payer contract | The hospital's agreement with a payer: price list, item lists, deadlines, settlement terms |
| Price list version | An effective-dated set of prices per service and room category |
| Package | A fixed price covering a defined set of services for a defined stay |
| Charge line | One priced service posted to an encounter |
| Patient share | The part of a bill the patient owes |
| Payer share | The part of a bill a payer owes |
| Non-payable | An item the payer will not pay for, per the payer's item lists |
| Proportionate deduction | Reduction of associated charges when the room occupied costs more than the policy entitles |
| Interim bill | An unnumbered statement of charges so far |
| Final bill | The numbered, immutable bill for an encounter |
| Bill of supply | The GST document for exempt supplies |
| Credit note, debit note | Documents that reduce or increase a finalised bill |
| Deposit | Money received against an encounter before billing |
| Refundable balance | Deposits and payments above the patient share |
| Shift | A cashier's working session, opened with a float and closed with a count |
| Pre-authorisation | A payer's approval, before or during a stay, of an amount it will pay |
| Enhancement | A request to increase an approved amount |
| Discharge authorisation | The payer's final approval required to discharge a cashless patient |
| Claim | The hospital's request to a payer for payment of its share |
| Deduction | An amount a payer declines to pay on a claim, with a reason |
| Fee share | The part of a doctor's billed fee paid to a visiting consultant |
| TDS | Tax deducted at source on fee payouts |
| IRP, IRN | The GST invoice registration portal and the number it assigns |
| NHCX | National Health Claims Exchange |
| ABHA | Ayushman Bharat Health Account identifier |
| DLT | TRAI's registry of SMS senders and templates |

## Appendix B — State machines

Permitted transitions only; any transition not listed is forbidden and must be rejected by the
application action, not merely hidden in the interface.

### B.1 Tenant
| From | To | Trigger and constraint |
|---|---|---|
| provisioning | active | first administrator accepts the invitation |
| active | suspended | platform operator suspends with a reason |
| suspended | active | platform operator reinstates with a reason |
| active | offboarding | platform operator offboards |
| suspended | offboarding | platform operator offboards |
| offboarding | erased | retention periods for all records have ended |

### B.2 Membership
| From | To | Trigger and constraint |
|---|---|---|
| invited | active | invitee accepts before expiry |
| invited | expired | invitation expiry passes |
| active | deactivated | administrator deactivates |
| deactivated | active | administrator reactivates |

### B.3 Patient
| From | To | Trigger and constraint |
|---|---|---|
| active | merged | merged into another patient; neither has an encounter in progress |

### B.4 Encounter
| From | To | Trigger and constraint |
|---|---|---|
| open | closed | OPD, day care or emergency: all bills settled and no claim open |
| open | cancelled | no charge posted |
| open | admitted | converted to an admission (FR-ENC-009) |
| admitted | discharge_initiated | discharge order or death recorded |
| admitted | cancelled | no charge posted |
| discharge_initiated | admitted | discharge order withdrawn before the final bill |
| discharge_initiated | discharged | final bill settled or balance accepted as due |
| discharged | closed | all bills settled and no claim open |

### B.5 Price list version
| From | To | Trigger and constraint |
|---|---|---|
| draft | published | no price above a ceiling; effective date not in the past |
| published | superseded | a later version of the same list becomes effective |
| draft | discarded | administrator discards |

### B.6 Charge line
| From | To | Trigger and constraint |
|---|---|---|
| held | posted | exception resolved with a known service code |
| held | discarded | exception discarded with a reason |
| posted | reversed | reversal line posted; line not on a final bill |
| posted | billed | included in a finalised bill |

### B.7 Bill
| From | To | Trigger and constraint |
|---|---|---|
| draft | finalised | no held charges on the encounter; mandatory recipient details present |
| finalised | partially_settled | a payment, deposit application or settlement reduces but does not clear it |
| finalised | settled | patient share and every payer share cleared or accepted as due |
| partially_settled | settled | the remaining shares are cleared |
| finalised | cancelled | approved; no payment or claim applied |

### B.8 Estimate
| From | To | Trigger and constraint |
|---|---|---|
| issued | accepted | patient accepts |
| issued | superseded | a newer estimate is issued for the same encounter |
| accepted | superseded | a newer estimate is issued and accepted |
| issued | lapsed | validity period passes |

### B.9 Approval request
| From | To | Trigger and constraint |
|---|---|---|
| pending | approved | approver is not the requester and holds approval permission |
| pending | rejected | approver rejects with a reason |
| pending | withdrawn | requester withdraws |

### B.10 Receipt
| From | To | Trigger and constraint |
|---|---|---|
| issued | cancelled | by the issuing cashier in the open shift, or with approval |

### B.11 Gateway payment request
| From | To | Trigger and constraint |
|---|---|---|
| initiated | confirmed | gateway confirms the requested amount |
| initiated | failed | gateway reports failure |
| initiated | held_for_review | gateway confirms a different amount |
| initiated | expired | no confirmation within the status-poll limit and the gateway reports none |
| held_for_review | confirmed | finance manager accepts the amount |

### B.12 Refund
| From | To | Trigger and constraint |
|---|---|---|
| requested | approved | approved per FR-AUTHZ-005 |
| requested | rejected | approver rejects |
| approved | paid | payment made; voucher issued |
| approved | failed | gateway or bank refund fails |
| failed | approved | retried |

### B.13 Cashier shift
| From | To | Trigger and constraint |
|---|---|---|
| open | closed | count recorded |
| closed | reconciled | variance zero, or explanation recorded by a finance manager |

### B.14 Payer contract
| From | To | Trigger and constraint |
|---|---|---|
| draft | active | no overlapping active contract for the payer and facility |
| active | expired | validity period ends |
| active | terminated | administrator terminates with a reason |

### B.15 Pre-authorisation
| From | To | Trigger and constraint |
|---|---|---|
| draft | submitted | required documents attached |
| submitted | query | payer raises a query; clock paused |
| query | submitted | query answered; clock resumes |
| submitted | approved | payer approves in full |
| submitted | partially_approved | payer approves a lower amount |
| submitted | denied | payer denies |
| approved | enhancement_submitted | enhancement requested |
| partially_approved | enhancement_submitted | enhancement requested |
| enhancement_submitted | approved | payer approves the enhancement |
| enhancement_submitted | partially_approved | payer approves part of the enhancement |
| draft | cancelled | insurance executive cancels |
| submitted | cancelled | patient withdraws the cashless request |

### B.16 Discharge authorisation
| From | To | Trigger and constraint |
|---|---|---|
| requested | approved | payer approves the final amount |
| requested | breached | deadline passes with no decision |
| breached | approved | payer approves after the deadline |
| requested | query | payer raises a query |
| query | requested | query answered |

### B.17 Claim
| From | To | Trigger and constraint |
|---|---|---|
| draft | submitted | documents attached; within window or condonation reason recorded |
| submitted | query_raised | payer query recorded |
| query_raised | submitted | answer submitted |
| submitted | settled | settlement recorded with no deduction |
| submitted | partially_settled | settlement recorded with deductions |
| submitted | denied | payer denies |
| partially_settled | closed | every deduction routed |
| settled | closed | automatic |
| denied | closed | amount routed to patient, dispute or write-off |

### B.18 E-invoice submission
| From | To | Trigger and constraint |
|---|---|---|
| pending | registered | IRP returns an IRN |
| pending | failed | IRP rejects |
| failed | pending | resubmitted after correction |
| registered | cancelled | cancelled at the IRP within its cancellation window |

### B.19 Notification
| From | To | Trigger and constraint |
|---|---|---|
| queued | sent | provider accepts |
| queued | suppressed | no DLT template, or recipient opted out of a non-transactional message |
| sent | delivered | provider reports delivery |
| sent | failed | provider reports failure after retries |

### B.20 Fee payout
| From | To | Trigger and constraint |
|---|---|---|
| draft | approved | finance manager approves |
| approved | paid | payment recorded; TDS recorded |
| draft | discarded | finance manager discards |

### B.21 Support consent
| From | To | Trigger and constraint |
|---|---|---|
| granted | expired | expiry time passes |
| granted | revoked | tenant administrator revokes |

## Appendix C — Communication matrix

| Id | Event | Recipient | Channels | Timing | Class |
|---|---|---|---|---|---|
| MSG-001 | Member invited | invitee | email | immediate | transactional |
| MSG-002 | Password reset requested | member | email | immediate | transactional |
| MSG-003 | Account locked | member | email | immediate | transactional |
| MSG-004 | Patient registered | patient | SMS | immediate | transactional |
| MSG-005 | Estimate issued | patient | SMS, WhatsApp | immediate | transactional |
| MSG-006 | Deposit received | patient | SMS, WhatsApp | immediate | transactional |
| MSG-007 | Payment received | patient | SMS, WhatsApp | immediate | transactional |
| MSG-008 | Final bill issued | patient | SMS, WhatsApp, email | immediate | transactional |
| MSG-009 | Refund paid | patient | SMS, WhatsApp | immediate | transactional |
| MSG-010 | Running charges exceed estimate | billing executive | in-app, email | immediate | staff alert |
| MSG-011 | Pre-authorisation deadline near | insurance executive | in-app, email | at warning period | staff alert |
| MSG-012 | Pre-authorisation decision recorded | patient | SMS | immediate | transactional |
| MSG-013 | Enhancement threshold reached | insurance executive | in-app | immediate | staff alert |
| MSG-014 | Discharge authorisation deadline near | insurance executive | in-app, email | at warning period | staff alert |
| MSG-015 | Claim submission window near | insurance executive | in-app, email | at warning period | staff alert |
| MSG-016 | Claim overdue for settlement | insurance executive | in-app | daily | staff alert |
| MSG-017 | E-invoice registration failing near window end | finance manager | in-app, email | immediate | staff alert |
| MSG-018 | Shift closed with variance | finance manager | in-app | immediate | staff alert |
| MSG-019 | Approval requested | approvers | in-app | immediate | staff alert |
| MSG-020 | Breach recorded | data-protection contact, platform operator | email | immediate | staff alert |
| MSG-021 | Scheduled job failed for a tenant | platform operator | email | immediate | staff alert |
| MSG-022 | Maintenance scheduled | all members | in-app | from lead time | staff alert |
| MSG-023 | Debit note for claim deduction | patient | SMS, WhatsApp | immediate | transactional |

## Appendix D — Role capability summary

Object-level rules constrain further: a role applies only in the facilities it was granted for.

| Capability | Registrar | Cashier | Billing exec | Insurance exec | Finance mgr | Administrator |
|---|---|---|---|---|---|---|
| Register and merge patients | yes | | merge | | | |
| Open, convert and cancel encounters | yes | | | | | |
| Change financial class | | | yes | yes | | |
| Post and reverse charges | | | yes | | | |
| Interim and final bills; estimates | | | yes | | | |
| Discount within limit | | | yes | | yes | |
| Approve discounts, cancellations, refunds, write-offs | | | | | yes | yes |
| Deposits, payments, receipts; shifts | | yes | | | | |
| Pre-authorisations and claims | | | | yes | | |
| Fee payouts, write-offs, exports, GST summary | | | | | yes | |
| Configure facilities, tariffs, payers, roles | | | | | | yes |
| Search audit log | | | | | yes | yes |

## Appendix E — Requirement summary

| Prefix | Domain | Section |
|---|---|---|
| TEN | Tenancy and organisation | 6 |
| ACC | Accounts | 7 |
| AUTHZ | Access control | 8 |
| PAT | Patients | 9 |
| ENC | Encounters | 10 |
| TAR | Tariffs and packages | 11 |
| CHG | Charges | 12 |
| BIL | Bills | 13 |
| TAX | GST and e-invoicing | 14 |
| PAY | Payments, deposits and refunds | 15 |
| PYR | Payers and contracts | 16 |
| CLM | Pre-authorisation and claims | 17 |
| FEE | Doctor fee share and TDS | 18 |
| AR | Receivables and accounting export | 19 |
| NOT | Notifications | 20 |
| AUD | Audit and data protection | 21 |
| OPS | Platform operations | 22 |
| RPT | Reports | 23 |
| NFR | Non-functional requirements | Part IV |
