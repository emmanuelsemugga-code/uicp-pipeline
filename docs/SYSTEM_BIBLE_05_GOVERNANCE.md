```markdown
# UICP System Bible — Part 5: Governance

**Version 1.0 — June 2026**
**Audience:** Compliance officers, auditors, regulators, grant committees,
and any organisation evaluating UICP against regulatory frameworks.

---

This document is the single entry point for all governance‑related
questions about UICP. It summarises UICP's alignment with the NIST AI
Risk Management Framework, the EU AI Act, GDPR, and the SOC 2 Type II
audit framework. Where detailed documents exist, they are referenced
rather than duplicated.

---

## 1. NIST AI RMF ALIGNMENT

The NIST AI Risk Management Framework (version 1.1, 2025) defines four
core functions: **GOVERN, MAP, MEASURE, and MANAGE.** UICP aligns with
all four.

### GOVERN — Establishing Policies, Roles, and Accountability

**What NIST requires:** Organisations must establish structures, policies,
and accountability mechanisms for their AI systems.

**How UICP satisfies this:**
- **Constraint Commitment (GAP‑11):** Every constraint set is
  cryptographically committed by an authorised operator with an Ed25519
  digital signature. The commitment is immutable and auditable.
- **Two‑Person Signing (GAP‑11):** Production deployments require two
  independent operator signatures before a constraint set activates.
- **Operator Registry (GAP‑11):** Only registered operators can sign
  commitments. Unregistered parties are rejected.
- **Key Lifecycle Management (GAP‑13/14):** All signing keys have defined
  validity periods, rotation procedures, and emergency revocation.
- **AI Asset Inventory Protocol (GAP‑05):** Every AI model in production
  must have a corresponding entry in the AI Asset Register, referencing
  a specific, versioned constraint set and extraction schema.
- **Regulatory Content Governance (GAP‑51):** When regulations change,
  the Regulatory Change Register tracks the change, maps it to affected
  constraint sets, and ensures constraints are updated within compliance
  timelines.

**Detailed document:** `docs/NIST_GOVERN_ALIGNMENT.md`

### MAP — Identifying AI Systems and Characterising Risks

**What NIST requires:** Organisations must establish the context of every
AI system they operate — what it does, who it affects, what risks it
poses.

**How UICP satisfies this:**
- **AI Asset Inventory:** Every governed AI model is registered with its
  purpose, input data, output format, risk classification, and governing
  constraint set.
- **Dependency Analysis (GAP‑16):** Every constraint's variable‑level
  dependencies are mapped. Impact chains, circular dependencies, and
  tight coupling are detected before deployment.
- **Residual Risk Register:** All known risks that cannot be eliminated
  are documented with mitigation strategies and review cadences.
- **Failure Mode Analysis:** False ALLOW, false BLOCK, gateway crash,
  key compromise, and audit log tampering are all documented with
  assigned ownership and response procedures.

**Detailed document:** `docs/NIST_RMF_OPERATIONAL_PROCEDURES.md`

### MEASURE — Monitoring Performance, Bias, and Drift

**What NIST requires:** Organisations must continuously monitor AI system
performance, detect degradation, and track bias.

**How UICP satisfies this:**
- **Performance Profiler (GAP‑48):** Per‑request metrics with p50/p95/p99
  percentile calculation, baseline comparison, and alert detection.
- **Constraint Analytics (GAP‑34):** Tracks which constraints fire most
  often, which are never triggered, and trends over time.
- **Constraint Staleness Detection (GAP‑48):** Flags constraints that
  have not been reviewed within a configurable window (default 6 months).
- **Alert Manager (GAP‑50):** Creates, deduplicates, escalates, and
  tracks alerts for critical system events across Slack, email, and
  PagerDuty.

**Detailed document:** `docs/NIST_RMF_OPERATIONAL_PROCEDURES.md`

### MANAGE — Mitigating Risks and Responding to Incidents

**What NIST requires:** Organisations must actively manage identified
risks, respond to incidents, and improve continuously.

**How UICP satisfies this:**
- **Fail‑Safe Enforcement (GAP‑21):** If the gateway is unavailable or
  encounters an internal error, it returns GATEWAY_UNAVAILABLE — never
  ALLOW. There is no silent failure path.
- **Version Control and Rollback (GAP‑15):** Constraint sets can be
  rolled back to any previous version with a documented reason.
- **Canary Deployment (GAP‑17):** Progressive rollout (1% → 10% → 50% →
  100%) with automatic rollback if approval rates drop or error rates
  spike.
- **Incident Response Procedure:** Documented, step‑by‑step response for
  gateway unavailability, unexpected BLOCK rates, key compromise, and
  audit log tampering. Response times, escalation paths, and
  communication templates are defined.
- **Business Continuity Plan:** Recovery objectives (RTO 4 hours, RPO
  1 hour), backup schedules, failover procedures, and disaster recovery
  testing.

**Detailed documents:** `docs/INCIDENT_RESPONSE.md`,
`docs/BUSINESS_CONTINUITY_PLAN.md`

---

## 2. EU AI ACT COMPLIANCE

The EU AI Act (effective in phases through 2026) classifies AI systems
based on risk and imposes obligations on providers and deployers.

### Article 6 — High‑Risk Classification

UICP materially influences decisions made by AI systems, but does not
determine them. Under the Q2 2026 Regulatory Guidance, UICP qualifies as
an "AI governance enabler" and is subject to modified Article 6
requirements: it must be auditable, must have governance documentation,
and must have technical testing logs.

UICP satisfies all three:
- **Auditable:** The enforcement log is cryptographically signed and
  immutable. Every decision can be replayed with identical inputs.
- **Governance documentation:** This System Bible, the Legal Assessment,
  and the NIST alignment documents satisfy the documentation requirement.
- **Testing logs:** 235+ automated tests across five engine phases, all
  passing, with results retained in the public repository.

### Article 11 — Technical Documentation

The EU AI Act requires that high‑risk AI systems be accompanied by
technical documentation describing the system's design, purpose, and
behaviour. The complete UICP System Bible (Parts 1‑9), together with the
Architecture Specification and Security Model, constitutes this
documentation.

### Article 16 — Transparency

Deployers of UICP must disclose to data subjects that UICP is involved
in the decision process. The Operator Manual provides a disclosure
template that clients can customise. The template includes information
about the constraints that were checked and a link to the deployer's
governance documentation.

### Article 82 — Liability

The Act establishes a presumption of liability: if an AI system's
decision harms a person, the provider is liable unless it proves the
harm was not caused by the system. UICP's liability is narrowly scoped:
- UICP is liable if the enforcement engine fails to enforce a constraint
  correctly (a bug in Phase 4 or Phase 5).
- UICP is NOT liable if the constraint itself was wrong, the extraction
  schema was inaccurate, or the deployer made an incorrect decision based
  on UICP's ALLOW output.

This liability boundary is documented in the Legal Assessment and in
every client agreement.

**Detailed document:** `docs/LEGAL_ASSESSMENT.md`

---

## 3. GDPR COMPLIANCE

UICP processes personal data — numeric binding values extracted from
model outputs — for the purpose of constraint enforcement and audit
trail maintenance.

### Article 5 — Data Minimisation

UICP collects only the variables needed for constraint evaluation
(e.g., age, income, risk score). Original model outputs are not retained.
Extracted binding values are replaced with SHA‑256 hash pointers in the
audit chain. Raw values are stored off‑chain in an encrypted personal
data store.

**Implementation:** GAP‑43 (Data Minimization), GAP‑44 (GDPR Erasure).

### Article 17 — Right to Erasure

Data subjects may request deletion of their personal data. UICP's
personal data store supports erasure: raw values are deleted while the
SHA‑256 hash pointer remains in the audit chain, proving enforcement
occurred while preserving chain integrity. The audit log records that
erasure occurred at a specific timestamp.

**Implementation:** GAP‑44 (GDPR Erasure Conflict), GAP‑45 (Access
Controls & Encryption).

### Article 30 — Records of Processing Activities

UICP maintains a complete, immutable record of all processing activities
in the audit chain. The Access Control Specification defines who can
access which data. Every read, write, and erasure of the personal data
store is logged with timestamp, role, operation type, and pseudonymised
record identifier.

### Article 32 — Security of Processing

UICP implements:
- Encryption at rest (AES‑256‑GCM for the personal data store).
- Encryption in transit (TLS 1.3 for API communication).
- Role‑based access control (gateway, auditor, operator roles).
- Access event logging.
- Key lifecycle management with rotation and revocation.

**Detailed document:** `docs/GDPR_PRIVACY_IMPACT_ASSESSMENT.md`

---

## 4. SOC 2 TYPE II AUDIT PLAN

UICP's architecture aligns with the Trust Service Criteria for SOC 2
Type II certification:

- **Common Criteria (CC):** Logical access control, system monitoring,
  and user authentication are implemented via API‑key authentication,
  role‑based access, and structured request logging.
- **Availability (A):** The Docker container includes a health check for
  orchestration platforms. Monitoring detects gateway unavailability
  within 60 seconds. The SLA defines uptime commitments per tier.
- **Integrity (I):** The append‑only cryptographic audit chain, Ed25519
  decision signatures, and standalone verifier provide mathematical
  proof of data integrity.

The SOC 2 Type II audit engagement will begin when UICP has a production
client generating real audit logs. The complete audit plan — including
firm selection, evidence collection, quarterly control testing, and
budget — is documented separately.

**Detailed documents:** `docs/RFP_SOC2_AUDIT.md`,
`docs/ACCESS_CONTROL_SPEC.md`

---

## 5. REGULATORY CONTENT GOVERNANCE

Regulations change. When they do, constraints must change with them.
UICP's Regulatory Content Governance Process defines exactly what
happens:

1. **Regulatory Change Register:** Every regulatory change that could
   affect constraint sets is recorded — the source, the date, the
   affected constraints, and the priority (CRITICAL if effective within
   30 days, HIGH within 90 days, STANDARD within 180 days).
2. **Impact Assessment:** The constraint owner determines which
   constraint sets are affected.
3. **Constraint Revision:** Updated constraints are drafted in canonical
   form.
4. **Validation:** The Constraint Validator checks for syntax errors,
   contradictions, and redundancy.
5. **Simulation:** The Simulation Engine replays historical decisions
   against the updated constraints to measure impact.
6. **Deployment:** The updated constraint set is deployed via canary
   rollout.
7. **Documentation:** The register entry is updated, the governance
   record is archived.

**Detailed document:** `docs/REGULATORY_CONTENT_GOVERNANCE.md`

---

## 6. INDEPENDENT VERIFICATION

Every governance claim in this document can be independently verified
without accessing the UICP enforcement engines.

The standalone `verify_uicp_bundle.py` script:
- Requires only Python 3.12 and the `cryptography` library.
- Verifies Ed25519 decision signatures, SHA‑256 chain integrity, and
  manifest export IDs.
- Contains zero UICP source code.
- Can be run by any regulator, auditor, grant committee, or third party.

To verify:
```bash
git clone https://github.com/emmanuelsemugga-code/uicp-pipeline.git
cd uicp-pipeline
python3 verify_uicp_bundle.py audit_export/ public_keys.json
```

If verification passes, the audit bundle is authentic, complete, and
was produced by the legitimate UICP enforcement gateway.

Detailed document: docs/INDEPENDENT_VERIFICATION_GUIDE.md

---

7. NEXT IN THE SYSTEM BIBLE

· Part 6 — Business: Pricing, contracts, intellectual property,
  engine protection doctrine, and client offboarding.
· Part 7 — Roles: Every job role required to operate UICP at scale,
  with skills, salary bands, and hiring triggers.
· Part 8 — Client‑Facing Resources: The onboarding checklist, the API
  reference, the knowledge base, and the client intake form.
· Part 9 — Appendices: Complete traceability — every GAP closed,
  every test result, every validation run, every adversarial evaluation.

```
