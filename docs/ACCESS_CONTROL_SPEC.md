# UICP Access Control Specification

## Version: 1.0.0
## Date: May 2026
## Status: Active

---

## Purpose

This document defines who can access which components of the UICP
enforcement system and under what conditions. It satisfies:
- GDPR Article 32 — technical measures for personal data security
- GDPR Article 30 — records of processing activities
- EU AI Act Article 9 — risk management system documentation

---

## Components and Classification

| Component | Contains Personal Data | Classification |
|---|---|---|
| `audit_chain/phase4_chain.json` | Hash pointers only | CONFIDENTIAL |
| `audit_chain/phase5_chain.json` | No personal data | INTERNAL |
| `audit_chain/manifest.json` | No personal data | INTERNAL |
| `offchain/personal_data_store.enc` | YES — raw binding values | RESTRICTED |
| `offchain/access_log.json` | Pseudonymized record IDs | CONFIDENTIAL |
| `engines/*.py` | No personal data | RESTRICTED |
| `docs/RESIDUAL_RISK_REGISTER.md` | No personal data | INTERNAL |

---

## Roles and Permissions

### Gateway Role
**Who:** The automated enforcement process only. Not a human.
**Can:** Write decisions, write personal data to encrypted store,
         perform erasure on data subject request.
**Cannot:** Modify constraint sets, access audit chain directly,
            read enforcement engine source code.

### Auditor Role
**Who:** Compliance officer, regulator, external auditor.
**Can:** Read audit chain files, read access log,
         read encrypted personal data store with auditor key.
**Cannot:** Write to any store, erase records, modify constraints,
            access enforcement engine source code.

### Operator Role
**Who:** Constraint author, system administrator.
**Can:** Define and register constraint sets, deploy gateway,
         rotate encryption keys with authorization.
**Cannot:** Read personal data store directly,
            modify audit chain records,
            bypass two-person signing requirement.

### Data Subject Role
**Who:** Individual whose data was processed.
**Can:** Request erasure via operator — operator instructs gateway
         to call erase() or erase_by_decision().
**Cannot:** Access any system component directly.

---

## Prototype Exception

**Current status:** Single-person prototype.
Emmanuel Semugga currently holds Gateway, Auditor, and Operator
roles simultaneously. This is documented as a prototype exception.

Before first regulated client deployment:
- Operator and Auditor roles must be separated
- Two-person signing must be enforced for constraint registration
- Gateway must run as automated process with no human login

---

## Encryption Requirements

| Asset | Encryption | Key Storage |
|---|---|---|
| `personal_data_store.enc` | AES-256-GCM | Separate from data file |
| Audit chain files | Not encrypted (hash pointers only) | N/A |
| Engine source files | Repository-level access control | GitHub private repo |

**Production key storage requirement:**
Encryption keys must be stored in a Hardware Security Module or
equivalent key management service. Environment variables are
acceptable only in development. Keys must never be stored in the
same directory as the encrypted data.

---

## Access Event Logging

Every read, write, and erasure of the PersonalDataStore is recorded
in `offchain/access_log.json` with:
- Timestamp (UTC ISO 8601)
- Role performing the operation
- Operation type (READ, WRITE, ERASE)
- Pseudonymized record identifier
- Operation detail

Access logs are retained for minimum 3 years per GDPR Article 30.

---

## Erasure Procedure

On receipt of a GDPR Article 17 erasure request:

1. Identify all `decision_id` values associated with the data subject
2. Call `gateway.erase_by_decision(decision_id)` for each
3. Verify erasure by calling `gateway.read(record_id)` — must return `actual_value: None`
4. Issue erasure confirmation to data subject within 30 days
5. Record erasure in access log — retained as evidence of compliance

---

## Review Cadence

This specification is reviewed quarterly or when:
- A new role is added to the team
- A new deployment environment is created
- A regulatory requirement changes
- A security incident occurs

**Next review due:** August 2026
