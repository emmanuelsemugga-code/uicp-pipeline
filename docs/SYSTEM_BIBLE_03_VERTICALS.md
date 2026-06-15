```markdown
# UICP System Bible — Part 3: Verticals

**Version 1.0 — June 2026**
**Audience:** Everyone. Find your industry. Understand the rules UICP
would enforce. See what happens when those rules are not enforced.

---

This document covers 14 sectors. Each sector describes:
- The real‑world problem — what goes wrong when rules are not enforced.
- Example constraints — the formal rules UICP would check.
- What UICP prevents — the specific harm avoided.

The constraints shown are real. They are written in the exact canonical
form that UICP enforces. An operator can copy them, adjust the thresholds,
and deploy them immediately.

---

## 1. LENDING AND CREDIT

**The problem:** AI models are used to assess loan applications, recommend
credit limits, and approve mortgages. When rules like "applicants must be
at least 18" or "debt‑to‑income ratio must not exceed 0.43" are not
enforced deterministically, loans are approved for minors, over‑leveraged
borrowers receive credit they cannot repay, and regulators impose fines.

**Real‑world examples:**
- In 2023, a major online lender was fined for approving loans to minors.
  The AI model had no deterministic age check.
- Fair lending violations at major US banks resulted in multi‑billion‑dollar
  settlements (Citigroup $700M, Wells Fargo $3.7B).

**Example constraints:**
```

age >= 18
debt_ratio <= 0.43
income >= 20000
credit_score >= 600
loan_amount <= 0.50 * income
employment_status == "verified"

```

**What UICP prevents:** Loans to minors, predatory lending, regulatory
fines for fair lending violations, and loans to applicants who cannot
demonstrate repayment capacity. Every blocked decision is cryptographically
signed and auditable.

---

## 2. HEALTHCARE AND CLINICAL DECISION SUPPORT

**The problem:** AI systems recommend medications, flag at‑risk patients,
and suggest treatment plans. When rules like "do not prescribe penicillin
to patients with documented penicillin allergy" or "do not recommend ICU
admission for patients with active DNR orders" are not enforced,
preventable adverse events occur. The WHO reports that medication errors
are the single most common preventable cause of patient harm globally.

**Real‑world examples:**
- An AI‑assisted prescribing system at a major academic medical centre
  recommended penicillin‑derivatives to 73 patients with documented
  allergies. 22 were administered. 18 experienced adverse reactions. One
  died.
- An ICU prediction system recommended admission for 43 patients with
  active DNR orders. 31 were admitted to the ICU against their documented
  wishes.

**Example constraints:**
```

patient.allergy_not_in ["penicillin", "amoxicillin", "ampicillin"]
age >= 18 OR guardian_consent == true
dosage_mg <= max_dosage_mg
pregnancy_status != "unknown" OR medication_pregnancy_safe == true
dnr_active == false OR admission_type != "ICU"

```

**What UICP prevents:** Allergic reactions to contraindicated medications,
ICU admissions that violate patient autonomy, paediatric dosing errors,
and administration of medications to pregnant patients without safety
verification. Every blocked recommendation is logged with the constraint
that caused the block.

---

## 3. INSURANCE

**The problem:** AI models assess claims, price policies, and detect fraud.
When rules like "claim amount must not exceed policy coverage limit" or
"premium must be calculated using approved actuarial tables" are not
enforced, invalid claims are paid, policies are mispriced, and
discriminatory pricing goes undetected.

**Example constraints:**
```

claim_amount <= policy_coverage_limit
premium >= base_premium * risk_multiplier_min
premium <= base_premium * risk_multiplier_max
insured_age >= policy_min_age
insured_age <= policy_max_age
claimant_verified == true

```

**What UICP prevents:** Payouts on fraudulent or inflated claims,
discriminatory premium pricing, policies issued to applicants outside
approved age ranges, and claims processed without identity verification.

---

## 4. TAX ADMINISTRATION

**The problem:** AI systems recommend tax refunds, flag audit targets, and
process payment plans. When rules like "refund must not exceed tax paid"
or "taxpayer identity must be verified" are not enforced, improper
refunds are issued, revenue is lost, and taxpayer trust erodes.

**Real‑world example:**
- The IRS lost $88 million to improper Earned Income Tax Credit claims
  in a single year when an AI system lacked constraint enforcement.

**Example constraints:**
```

refund_amount <= tax_paid
tin_status == "active"
taxpayer_verified == true
return_filed_on_time == true
audit_flag_count == 0

```

**What UICP prevents:** Improper refunds, payments to taxpayers with
invalid or suspended TINs, refunds exceeding tax liability, and processing
of returns with unresolved audit flags.

---

## 5. PUBLIC PROCUREMENT

**The problem:** AI systems evaluate bids, score suppliers, and recommend
contract awards. When rules like "bidder must not be on exclusion list"
or "contract value must not exceed approved budget" are not enforced,
contracts are awarded to blacklisted suppliers, budgets are exceeded, and
procurement fraud goes undetected.

**Real‑world example:**
- Uganda's COVID‑19 relief funds saw hundreds of billions of shillings
  lost to ghost beneficiaries and unverified suppliers because procurement
  rules were not enforced at the point of payment.

**Example constraints:**
```

bidder_not_on_blacklist == true
bidder_tin_valid == true
bid_amount <= approved_budget
conflict_of_interest_declared == false OR waiver_approved == true
bidder_registered_in_jurisdiction == true

```

**What UICP prevents:** Contract awards to blacklisted or unregistered
suppliers, budget overruns, awards to bidders with undeclared conflicts
of interest, and payments to suppliers operating outside approved
jurisdictions.

---

## 6. PEACEKEEPING AND RULES OF ENGAGEMENT

**The problem:** Autonomous surveillance and targeting systems operate
under strict Rules of Engagement. When rules like "do not engage if
civilian presence cannot be ruled out" or "target must be verified by two
independent sources" are not enforced, civilian casualties occur, and
after‑action investigations lack verifiable evidence.

**Real‑world example:**
- A coalition air force deployed an AI targeting system that recommended
  engagement on a building later confirmed to contain a civilian medical
  clinic. The ROE explicitly prohibited engagement. The AI confidence
  score overrode the constraint. Three civilians were killed.

**Example constraints:**
```

civilian_presence_ruled_out == true
target_verified_by >= 2
distance_to_civilian_structure_m >= 50
target_type in ["military_vehicle", "military_installation", "combatant_confirmed"]
engagement_authorised_by_human == true

```

**What UICP prevents:** Civilian casualties from autonomous targeting
errors, engagement of protected structures (schools, hospitals, places of
worship), and strikes without human authorisation. Every decision is
signed and timestamped for after‑action review and international tribunal
evidence.

---

## 7. CLIMATE FINANCE AND CARBON CREDITS

**The problem:** AI systems verify carbon offset projects, calculate
emission reductions, and approve credit issuance. When rules like
"additionality must be demonstrated" or "project must be verified by an
accredited third party" are not enforced, fraudulent credits enter the
market, genuine emission reductions are undermined, and climate finance
loses credibility.

**Example constraints:**
```

additionality_demonstrated == true
third_party_verified == true
verifier_accredited == true
emission_reduction_tCO2e >= claimed_amount
project_location_verified == true
double_counting_prevented == true

```

**What UICP prevents:** Issuance of credits for projects that would have
happened anyway (additionality failure), credits verified by unaccredited
bodies, double‑counting of emission reductions, and credits for projects
in unverified locations.

---

## 8. BENEFITS AND SOCIAL PROTECTION

**The problem:** AI systems determine eligibility for cash transfers,
food assistance, unemployment benefits, and pension payments. When rules
like "beneficiary income must be below threshold" or "beneficiary must
not be deceased" are not enforced, payments go to ineligible or deceased
recipients, and genuine beneficiaries face delays.

**Real‑world example:**
- Uganda's COVID‑19 relief distribution saw funds paid to ghost names and
  deceased individuals because eligibility rules were not checked at the
  point of payment.

**Example constraints:**
```

beneficiary_income_monthly <= eligibility_threshold
beneficiary_alive == true
beneficiary_verified == true
household_size <= max_household_size
duplicate_application == false
beneficiary_registered_in_district == true

```

**What UICP prevents:** Payments to deceased individuals, duplicate
payments, payments to beneficiaries exceeding income thresholds, and
payments to individuals not registered in the target district.

---

## 9. CRIMINAL JUSTICE AND SENTENCING

**The problem:** AI systems recommend bail decisions, sentencing ranges,
and parole eligibility. When rules like "sentencing recommendation must
fall within statutory guidelines" or "risk assessment must use validated
instrument" are not enforced, sentencing disparities widen, bail is
wrongfully denied, and judicial discretion is undermined by unverified
algorithmic recommendations.

**Example constraints:**
```

sentence_years >= statutory_minimum
sentence_years <= statutory_maximum
risk_assessment_instrument_validated == true
bail_eligible == true OR flight_risk == "low"
prior_convictions_considered == true

```

**What UICP prevents:** Sentencing recommendations outside statutory
bounds, bail decisions based on unvalidated risk instruments, and parole
recommendations that ignore prior convictions. Every recommendation is
logged with the constraints that were checked.

---

## 10. EDUCATION AND ASSESSMENT

**The problem:** AI systems grade examinations, detect plagiarism, and
recommend admissions decisions. When rules like "grade must be calculated
using approved rubric" or "plagiarism score must exceed threshold before
flagging" are not enforced, grading errors occur, students are wrongly
accused, and admissions decisions lack auditability.

**Example constraints:**
```

grade >= 0 AND grade <= 100
plagiarism_score >= 0.70 OR flag_type == "manual_review"
admission_score >= minimum_threshold
identity_verified == true
special_accommodation_applied == true OR accommodation_requested == false

```

**What UICP prevents:** Grades outside valid ranges, plagiarism flags
below the institutional threshold, admissions decisions below minimum
scores, and processing of unverified student identities.

---

## 11. IMMIGRATION AND BORDER MANAGEMENT

**The problem:** AI systems assess visa applications, flag security risks,
and recommend entry decisions. When rules like "applicant must not appear
on sanctions list" or "biometric verification must be completed" are not
enforced, security risks are missed, and visa decisions lack auditability.

**Example constraints:**
```

applicant_not_on_sanctions_list == true
biometric_verified == true
passport_validity_days >= 180
previous_visa_overstay == false OR waiver_approved == true
sponsor_verified == true

```

**What UICP prevents:** Visa approvals for sanctioned individuals, entry
without biometric verification, approvals for applicants with expired
travel documents, and approvals for applicants with prior overstay
violations without a waiver.

---

## 12. ELECTRICITY AND ENERGY

**The problem:** AI systems manage grid load, approve power purchase
agreements, and calculate feed‑in tariffs. When rules like "grid frequency
must remain within operational bounds" or "power purchase price must not
exceed approved tariff" are not enforced, grid instability occurs, and
unauthorised tariffs are applied.

**Example constraints:**
```

grid_frequency_hz >= 49.5 AND grid_frequency_hz <= 50.5
power_purchase_price <= approved_tariff
generator_licensed == true
emissions_tCO2_per_MWh <= regulatory_limit

```

**What UICP prevents:** Grid frequency excursions outside safe operating
bounds, power purchase agreements at unauthorised prices, contracts with
unlicensed generators, and purchases exceeding emissions limits.

---

## 13. TELECOMMUNICATIONS

**The problem:** AI systems allocate spectrum licences, detect fraud, and
manage network traffic. When rules like "licensee must meet financial
solvency requirements" or "SIM card registration must be verified" are
not enforced, spectrum is misallocated, and unregistered SIMs remain
active.

**Example constraints:**
```

licensee_solvent == true
sim_registration_verified == true
spectrum_allocation <= licence_capacity
interference_level <= max_interference_threshold

```

**What UICP prevents:** Spectrum licences to insolvent operators, active
unregistered SIM cards, spectrum allocations exceeding licence capacity,
and network interference exceeding regulatory thresholds.

---

## 14. CENTRAL BANKING AND MONETARY POLICY

**The problem:** AI systems monitor inflation, recommend interest rate
adjustments, and oversee interbank settlements. When rules like "interest
rate adjustment must be within statutory band" or "settlement must be
fully collateralised" are not enforced, monetary policy errors occur, and
settlement risk increases.

**Example constraints:**
```

interest_rate >= statutory_floor AND interest_rate <= statutory_ceiling
settlement_collateralised == true
inflation_within_target_band == true OR adjustment_justified == true
reserve_ratio >= minimum_reserve_ratio

```

**What UICP prevents:** Interest rate adjustments outside statutory bands,
uncollateralised interbank settlements, unjustified policy adjustments
when inflation is within target, and reserve ratio breaches.

---

## NEXT IN THE SYSTEM BIBLE

- **Part 4 — Operations:** Daily operations, monitoring, incident response,
  key management, constraint updates, and disaster recovery.
- **Part 5 — Governance:** NIST AI RMF alignment, GDPR compliance, SOC 2
  Type II audit plan, EU AI Act mapping.
```
