# UICP GDPR Privacy Impact Assessment (DPIA)

## Version 1.0 — Pilot‑Ready
### Status: Active
### Audience: Data Protection Officers, Compliance Officers, Auditors

---

## 1. EXECUTIVE SUMMARY

UICP is a deterministic constraint enforcement gateway. It receives outputs from AI models, extracts structured data (bindings) from those outputs, evaluates the bindings against formal constraints, and records a cryptographically signed enforcement decision. The system processes personal data during this operation.

This Data Protection Impact Assessment (DPIA) is conducted in accordance with Article 35 of the General Data Protection Regulation (Regulation 2016/679). It identifies the personal data processed, assesses the necessity and proportionality of that processing, evaluates the risks to data subjects, and documents the technical and organisational measures in place to mitigate those risks.

The conclusion of this assessment is that UICP's processing of personal data is necessary, proportionate, and adequately protected. Residual risks are identified and accepted or mitigated as documented below.

---

## 2. DATA PROCESSING DESCRIPTION

### 2.1 Nature of Processing

UICP processes personal data for the sole purpose of constraint enforcement and audit trail maintenance. The processing is deterministic — the same inputs always produce the same outputs. UICP does not learn from data, does not profile individuals, and does not make decisions about individuals.

### 2.2 Scope of Processing

**Data categories processed:**
- Extracted binding values: numeric data extracted from model outputs (e.g., age, income, credit score, risk rating, debt‑to‑income ratio).
- Audit log entries: decision status (ALLOW/BLOCK), constraint identity, violation details, timestamps.
- Request metadata: output_id, timestamp, API key (masked in logs).

**Data categories NOT processed:**
- Raw model output text is never stored.
- Names, addresses, national identification numbers, biometric data, or other directly identifying personal data are not extracted or stored.
- UICP does not perform profiling, automated decision‑making, or any form of machine learning.

### 2.3 Context of Processing

UICP is deployed as infrastructure by the client organisation. The client defines the extraction schema (which variables to extract) and the constraint set (which rules to enforce). UICP does not determine the purpose of processing — the client does.

### 2.4 Purposes of Processing

The processing has a single, clearly defined purpose: to enforce the client's governance constraints on AI model outputs and to maintain an auditable record of that enforcement. This purpose is legitimate under GDPR Article 6(1)(f) — the legitimate interest of the client in ensuring their AI systems operate within defined safety and compliance boundaries.

---

## 3. NECESSITY AND PROPORTIONALITY ASSESSMENT

### 3.1 Necessity

Constraint enforcement requires access to the specific data values that the constraints reference. If a constraint states "age >= 18", UICP must process the applicant's age to evaluate that constraint. Processing is the minimum necessary to achieve the enforcement purpose.

### 3.2 Proportionality

UICP minimises personal data processing by design:
- Raw model outputs are never stored. Only the extracted numeric bindings are retained.
- Data retention is configurable. The default is 30 days for raw binding values. After retention, raw values are deleted; cryptographic hashes remain for audit integrity.
- Personal data is encrypted at rest using AES‑256‑GCM.
- Data is never used for any secondary purpose (profiling, marketing, analytics).
- Access to personal data is restricted by role‑based access control.

### 3.3 Data Minimisation Measures

| Measure | Implementation |
|---------|---------------|
| Raw model output not stored | Extraction layer processes text in memory; only bindings are stored |
| Configurable retention | Default 30 days; operator can set shorter or longer |
| Off‑chain personal data | Raw values stored in encrypted PersonalDataStore, not in audit chain |
| Cryptographic hashes in chain | Only SHA‑256 hashes of values appear in the immutable audit log |
| Erasure support | GDPR Article 17 erasure deletes raw values while preserving audit integrity |

---

## 4. RISK ASSESSMENT

### 4.1 Identified Risks

**Risk 1: Unauthorised access to personal data store**
- Likelihood: Low
- Impact: Medium (exposure of numeric binding values)
- Mitigation: AES‑256‑GCM encryption at rest; role‑based access control; all access logged

**Risk 2: Inability to comply with erasure requests**
- Likelihood: Low
- Impact: High (GDPR Article 17 violation)
- Mitigation: Personal data stored off‑chain in erasable store; erasure procedure documented and tested

**Risk 3: Excessive data retention**
- Likelihood: Low
- Impact: Medium (GDPR Article 5(1)(e) violation)
- Mitigation: Configurable retention with default 30 days; automatic purging of expired data

**Risk 4: Data breach via compromised encryption key**
- Likelihood: Low
- Impact: High (exposure of all stored personal data)
- Mitigation: Key lifecycle management with rotation and emergency revocation; production HSM requirement

**Risk 5: Personal data in audit logs accessible to unauthorised parties**
- Likelihood: Low
- Impact: Medium
- Mitigation: Audit logs contain only SHA‑256 hashes of personal values, not raw data; logs are append‑only and access‑controlled

### 4.2 Risk Acceptance

All identified risks are either mitigated to an acceptable level or accepted with documented justification. No unmitigated high‑impact risks remain.

---

## 5. DATA SUBJECT RIGHTS

UICP supports the following data subject rights under GDPR:

| Right | Support | Implementation |
|-------|---------|---------------|
| Right of access (Art. 15) | Supported | Client can query audit log and personal data store per data subject |
| Right to rectification (Art. 16) | Supported | Client can update binding values in personal data store |
| Right to erasure (Art. 17) | Supported | Raw values deleted from personal data store; hash remains in audit chain |
| Right to restriction (Art. 18) | Supported | Client can suspend processing for specific data subjects |
| Right to data portability (Art. 20) | Supported | Client can export decision records in machine‑readable JSON format |
| Right to object (Art. 21) | Supported | Client can deactivate constraint enforcement for specific use cases |
| Automated decision‑making (Art. 22) | Not applicable | UICP does not make decisions; it only enforces constraints |

---

## 6. SECURITY MEASURES

UICP implements the following technical and organisational security measures:

| Measure | Implementation |
|---------|---------------|
| Encryption at rest | AES‑256‑GCM for personal data store |
| Encryption in transit | TLS for all API communication |
| Access control | Role‑based (gateway, auditor, operator) |
| Authentication | API key required for all enforcement requests |
| Audit logging | All access to personal data is logged with timestamp, role, and operation |
| Key lifecycle | Rotation every 12 months; emergency revocation |
| Fail‑safe | On error, defaults to BLOCK and manual review, never silent ALLOW |
| Testing | 73/73 enforcement tests, 101/101 audit tests, 58/58 fail‑safe tests |

---

## 7. DATA PROCESSING AGREEMENT (DPA) REQUIREMENTS

Clients deploying UICP must have a Data Processing Agreement in place. The DPA must specify:

- The categories of personal data processed (see Section 2.2)
- The purpose of processing (see Section 2.4)
- The duration of processing (retention period)
- The security measures implemented (see Section 6)
- Sub‑processor arrangements (currently none; any future sub‑processor requires client notification and consent)
- Breach notification timeline (48 hours from confirmation of breach)
- International transfer mechanism (Standard Contractual Clauses included by default)

A template DPA is provided in `docs/DPA_TEMPLATE.md`.

---

## 8. DATA PROTECTION OFFICER (DPO) CONSULTATION

Under GDPR Article 35(2), the controller must consult the DPO when carrying out a DPIA. The client organisation deploying UICP is the controller. The client's DPO must:

1. Review this DPIA.
2. Confirm that the processing described is consistent with the client's data protection policies.
3. Advise on any additional measures required for the client's specific use case.

UICP provides this DPIA as evidence of the technical and organisational measures in place. The client's DPO is responsible for the final assessment in the context of the client's overall processing activities.

---

## 9. SUPERVISORY AUTHORITY CONSULTATION

Under GDPR Article 36, if the DPIA indicates that processing would result in a high risk in the absence of measures taken by the controller to mitigate the risk, the controller must consult the supervisory authority prior to processing. Based on the risk assessment in Section 4, UICP's processing does not present a high risk after mitigation. Therefore, prior consultation is not required for UICP itself. However, the client's overall AI system may require consultation depending on its specific use case and risk profile.

---

## 10. REVIEW AND APPROVAL

This DPIA must be reviewed:

- Annually.
- When a new data category is added to UICP's processing.
- When a new deployment environment introduces new risks.
- After any personal data breach.

**Prepared by:** UICP development team
**Date:** June 2026
**Next review due:** June 2027

---

**END OF GDPR PRIVACY IMPACT ASSESSMENT**
