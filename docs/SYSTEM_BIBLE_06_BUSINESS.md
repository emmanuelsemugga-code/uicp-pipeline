```markdown
# UICP System Bible — Part 6: Business

**Version 1.0 — June 2026**
**Audience:** CFOs, procurement officers, business decision-makers,
grant committees, and anyone evaluating UICP from a commercial
perspective.

---

This document covers the commercial framework for UICP: pricing,
contracts, intellectual property, the engine protection doctrine,
and client offboarding. Where detailed templates exist, they are
referenced rather than duplicated.

---

## 1. PRICING MODEL

UICP is offered under a three‑tier model designed to accommodate
pilot evaluation, production deployment, and enterprise‑scale
regulated environments.

| Tier | Price | Decisions/Month | Constraint Sets | Tenants | SLA | Support |
|------|-------|-----------------|-----------------|---------|-----|---------|
| **Pilot** | Free | 1,000 | 1 | 1 | None | GitHub Issues |
| **Standard** | $500/month | 100,000 | 5 | 3 | 99.5% (business hours) | Email (1 business day) |
| **Enterprise** | $2,000/month | Unlimited | Unlimited | Unlimited | 99.9% (24/7) | Email + Phone (4 hours) |

### Add‑ons (Standard Tier)
- Additional 100,000 decisions/month: $100/month
- Additional constraint set: $50/month
- Additional tenant: $75/month

### Volume Discounts
Enterprise deployments exceeding 1,000,000 decisions per month are
eligible for volume pricing. Contact UICP directly for a quote.

### Payment Terms
- Invoices are issued monthly on the 1st of each month.
- Payment is due within 30 calendar days.
- Accepted methods: bank transfer (USD, EUR, UGX), mobile money
  (Uganda only), international wire transfer.
- Late payments may result in service suspension after 15 days'
  written notice.

**Detailed document:** `PRICING.md`

---

## 2. CONTRACT TEMPLATES

UICP provides standard contract templates for every stage of the
client relationship. All templates are in the public repository
and can be reviewed before any commitment is made.

### 2.1 Pilot Agreement

A 30‑day free pilot for organisations evaluating UICP. Covers:
- Scope of the pilot (up to 1,000 decisions/month, one constraint
  set).
- Responsibilities of both parties.
- Data handling and confidentiality.
- Limitations of liability.
- What happens at the end of the pilot (extend, convert to paid,
  or terminate with full audit log export).

The pilot requires no financial commitment. If UICP does not deliver
measurable protection against rule violations, the pilot partner
walks away with no obligation.

**Template:** `templates/PILOT_AGREEMENT.md`

### 2.2 Data Processing Agreement (DPA)

A GDPR‑compliant DPA that defines:
- Subject matter and duration of processing.
- Processor obligations (encryption, access control, breach
  notification, data subject rights support).
- Sub‑processor policy (none currently; notification required for
  any future engagement).
- Security measures (AES‑256‑GCM, TLS 1.3, role‑based access,
  access logging).
- International data transfer provisions.

**Template:** `templates/DATA_PROCESSING_AGREEMENT.md`

### 2.3 Master Service Agreement (MSA)

The paid production contract for Standard and Enterprise clients.
Covers:
- Services provided.
- Term (12 months, auto‑renewing) and termination conditions.
- Fees and payment terms.
- Client responsibilities (constraint correctness, extraction
  accuracy, final decision authority).
- Service Level Agreement with service credits for breach.
- Warranties (what UICP guarantees and what it does not).
- Limitation of liability.
- Intellectual property (UICP retains engine ownership; client
  retains data ownership).
- Confidentiality and governing law.

**Template:** `templates/MASTER_SERVICE_AGREEMENT.md`

---

## 3. INTELLECTUAL PROPERTY

### 3.1 What UICP Owns

UICP retains full ownership of:
- All five enforcement engines (`normalize_v05.py`, `phase2_engine.py`,
  `phase3_engine.py`, `phase4_engine.py`, `phase5_engine.py`).
- The internal pipeline algorithms — the exact sequence of
  transformations that produce canonical identities, detect semantic
  equivalence, perform multi‑variable canonicalization, enforce
  constraints, and construct the cryptographic audit chain.
- The UICP name, branding, and documentation.

### 3.2 What the Client Owns

The client retains full ownership of:
- All data sent to the UICP endpoint (model outputs, extracted
  bindings).
- All constraint sets and extraction schemas they define.
- All audit logs and decision records generated from their data.
- All cryptographic keys they generate and manage.

### 3.3 What Is Public

The public repository contains:
- Public wrappers — thin interfaces that expose validated output
  contracts without revealing internal algorithms.
- Verification scripts — automated tests that prove every claim
  without exposing internal logic.
- Standalone verifier — `verify_uicp_bundle.py`, which validates
  cryptographic proofs without any access to the enforcement
  engines.
- REST API layer — the complete Flask application is open for
  inspection.
- Tier 2 durability modules — validation framework, version control,
  dependency analysis, canary deployment, simulation engine, and more.
- Complete documentation — System Bible, architecture specification,
  security model, regulatory mapping, operator manual, legal
  assessment, and governance protocols.

### 3.4 What Is Protected

The five enforcement engine files are excluded from the public
repository via `.gitignore` and are never pushed. They are available
under controlled disclosure to:
- Paying clients (for deployment and integration).
- External auditors retained by clients (under NDA).
- Regulatory bodies with statutory authority (upon written request
  and protective order).

**Detailed document:** `docs/ENGINE_PROTECTION_DOCTRINE.md`

---

## 4. THE ENGINE PROTECTION DOCTRINE

UICP protects its core engines through controlled disclosure — the
same model used by every major infrastructure company. This is not
security through obscurity. It is trade‑secret protection for the
specific pipeline order, normalization algorithms, and enforcement
logic developed through rigorous adversarial testing.

### Why the engines are not open‑source

1. **Trade‑secret protection:** The pipeline order and internal
   algorithms are proprietary. Making them public would enable
   competitors to replicate the enforcement logic without
   investing in adversarial validation.
2. **Infrastructure precedent:** Google does not open‑source its
   search ranking algorithm. Cloudflare does not open‑source its
   DDoS mitigation engine. AWS does not open‑source its hypervisor.
   UICP follows the same model.
3. **Independent verification without engine access:** The standalone
   verifier proves that full cryptographic verification is possible
   without accessing the engines. Any regulator, auditor, or third
   party can verify UICP's claims with a single command.

### What happens if the engines leak

1. Trade‑secret status is preserved by the controlled disclosure
   model. Unauthorised publication constitutes trade‑secret
   misappropriation and is actionable.
2. The public verification mechanism remains intact. A competitor
   could re‑implement the engines, but the validation baseline —
   235+ automated tests, external adversarial reviews, and
   cryptographic proof — cannot be faked.
3. New engine versions would be released with updated validation
   baselines, making any leaked version obsolete within one release
   cycle.

**Detailed document:** `docs/ENGINE_PROTECTION_DOCTRINE.md`

---

## 5. CLIENT OFFBOARDING

When a client terminates their relationship with UICP — whether
at the end of a pilot, through non‑renewal, or through termination
for cause — the following procedures apply.

### 5.1 Data Export

Upon termination, UICP will:
- Export the complete audit log and deliver it to the client as a
  verifiable audit bundle (JSON files plus manifest and public keys).
- Export all constraint sets and extraction schemas in their
  canonical JSON format.
- Confirm with the client that the exported data is complete and
  verifiable.

### 5.2 Data Deletion

Within 30 days of termination, UICP will:
- Delete all personal data (extracted binding values) from the
  personal data store.
- Confirm deletion in writing.
- Retain the audit chain — which contains only SHA‑256 hash pointers,
  not raw personal data — per the client's retention policy or for
  the regulatory minimum (7 years for financial compliance).

### 5.3 API Key Revocation

API keys are disabled within 24 hours of termination. No further
enforcement decisions will be processed.

### 5.4 Contractual Obligations

- Confidentiality obligations survive termination for 3 years.
- The client's obligation to not reverse‑engineer UICP software
  survives termination indefinitely.
- Any outstanding invoices remain payable.

**Detailed document:** `docs/CLIENT_OFFBOARDING.md`

---

## 6. PAYMENT TERMS

- Invoices are issued on the **1st of each month** for the month ahead.
- Payment is due within **30 calendar days** of the invoice date.
- For new clients, the first invoice is pro‑rated for the remaining
  days of that month.
- Late reminders are sent at 7 and 14 days past due.
- After 30 days past due, UICP reserves the right to suspend service
  and apply a late fee of 1.5% per month on the outstanding balance.
- Service is restored within 1 business day of payment confirmation.
- UICP does not offer refunds for partial months of service. If UICP
  fails to meet the SLA, the client receives a service credit of 10%
  of the monthly fee, applied to the following month's invoice.

**Detailed document:** `docs/PAYMENT_TERMS.md`

---

## 7. NEXT IN THE SYSTEM BIBLE

- **Part 7 — Roles:** Every job role required to operate UICP at scale,
  with skills, salary bands, and hiring triggers.
- **Part 8 — Client‑Facing Resources:** The onboarding checklist, the API
  reference, the knowledge base, and the client intake form.
- **Part 9 — Appendices:** Complete traceability — every GAP closed,
  every test result, every validation run, every adversarial evaluation.
```
