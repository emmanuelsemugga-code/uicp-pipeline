# UICP Security Model

## Version 1.0 — Pilot-Ready
### Status: Aligned with Validated Architecture (GAP-28)
### Audience: Security Officers, Compliance Professionals, Auditors, Technical Decision-Makers

---

## EXECUTIVE SUMMARY

UICP is designed with a specific threat model in mind: **deterministic constraint enforcement in environments where AI model outputs cannot be trusted to comply with formal rules**. The system protects against threats where models produce recommendations that violate constraints, where attackers attempt to tamper with decisions, and where cryptographic keys might be compromised.

This document describes the complete security model: what threats UICP protects against, how it protects, what assumptions are required, and what cannot be protected. It is written for security officers who must decide whether to deploy UICP, and for auditors who must verify that security controls work.

**Key Security Properties (validated):**

- **Deterministic Decision-Making:** Same inputs always produce same enforcement decision (73/73 enforcement tests, 10,368 fuzz tests). No probabilistic override can bypass a constraint.
- **Decision Integrity:** Every decision is cryptographically signed with Ed25519 (101/101 signing tests). Decisions cannot be forged or modified without detection.
- **Audit Immutability:** The audit log is append-only and cryptographically chained (43/43 chain integrity tests). Historical records cannot be secretly modified.
- **Fail-Safe Defaults:** When UICP encounters an error it cannot safely recover from, it defaults to BLOCK and manual review, never to ALLOW (58/58 fail-safe tests).
- **Access Control:** Role-based access control (RBAC) with three distinct roles — gateway, auditor, operator — enforced at the API and data layer. Only authorized roles can access encryption keys, constraint sets, and audit logs.
- **Key Lifecycle Management:** Signing keys have defined validity periods (default 12 months), can be rotated, and can be revoked in emergency. Key lifecycle operations are cryptographically enforced (37/37 key lifecycle tests).

**Current Limitations (honest):**

- UICP currently runs as a single process. Redundancy and failover (GAP-20) are not yet implemented. A process crash requires manual restart.
- Multi-tenancy (GAP-18) is not yet implemented. Each deployment serves a single client.
- Constraint updates require a service restart (GAP-19). Zero-downtime rotation is planned but not yet available.
- The system has been validated in controlled testing environments, not in a live production deployment.

These limitations are documented openly. They are the top-priority infrastructure items in the funded work plan.

---

## THREAT MODEL: WHAT UICP PROTECTS AGAINST (AND WHAT IT DOES NOT)

A threat model defines the attacks a system is designed to prevent. UICP is designed to protect against specific threats in specific contexts. Understanding what UICP protects against is as important as understanding what it does not protect against.

### Threat 1: Constraint Violation in Model Outputs

**Description:** An AI model produces outputs that violate a formal constraint. For example, a loan approval model recommends approval for an applicant under 18, or a clinical decision system recommends a medication to which the patient is allergic.

**Protection:** UICP enforces constraints deterministically. The enforcement pipeline (Phases 1–4) evaluates every constraint against extracted bindings. If any constraint is violated, the decision is BLOCKed. No confidence score can override a constraint violation.

**Validation:** 73/73 enforcement tests, 10,368 fuzz tests with adversarial constraint sets. Zero violations slipped through.

**Limitation:** UICP can only enforce constraints that the client has defined and registered. If a constraint is missing, it cannot be enforced.

---

### Threat 2: Decision Tampering

**Description:** An attacker modifies a historical decision after it has been made — changing a BLOCK to an ALLOW in the audit log, or altering the bindings that were evaluated.

**Protection:** Phase 5 signs every decision with Ed25519 and appends it to an immutable, cryptographically chained audit log. Any modification breaks the signature and the hash chain, making tampering immediately detectable.

**Validation:** 101/101 signing tests, 43/43 audit log immutability tests.

**Limitation:** If an attacker obtains the signing key and can modify both the primary audit log and all external copies simultaneously, detection becomes impossible. This is a full-compromise scenario.

---

### Threat 3: Signature Forgery

**Description:** An attacker attempts to create a fake signature, making it appear that UICP approved a decision it actually rejected.

**Protection:** Ed25519 is mathematically unforgeable under standard cryptographic assumptions. The private key is never exposed in plaintext; it is encrypted at rest and accessible only to authorized operators via RBAC.

**Validation:** Ed25519 unforgeability is a mathematical property, not a per-implementation test. UICP's use of the algorithm has been validated by 101/101 signing tests confirming correct signature generation and verification.

**Limitation:** If the private key is compromised, forged signatures become possible. Key rotation and revocation are the mitigations.

---

### Threat 4: Constraint Bypass

**Description:** An attacker crafts a model output designed to evade constraint checking — using Unicode tricks, whitespace manipulation, or encoding exploits to cause the normalization or extraction phases to skip constraints.

**Protection:** Normalization is deterministic and collision-resistant. Extraction schemas are explicit and client-defined; if a model output does not match the schema, an error is returned rather than a false ALLOW.

**Validation:** 10,368 adversarial constraint sets tested; zero bypasses found.

**Limitation:** If the client's extraction schema is incorrectly written, UICP cannot detect it. The client is responsible for schema correctness.

---

### Threat 5: Denial of Service

**Description:** An attacker sends malformed inputs or oversized constraint sets designed to crash UICP or exhaust resources.

**Protection:** Input validation rejects malformed data. Complexity limits (maximum constraints, maximum computation time) prevent resource exhaustion. When limits are exceeded, UICP returns GATEWAY_UNAVAILABLE rather than crashing.

**Validation:** 58/58 fail-safe tests confirm graceful degradation.

**Limitation:** UICP currently runs as a single process with no automatic restart. A crash requires manual intervention (GAP-20).

---

### Threat 6: Encryption Key Compromise

**Description:** An attacker obtains the Ed25519 signing key or the AES-256 personal data encryption key.

**Protection:** Keys are encrypted at rest, protected by RBAC, and never transmitted in plaintext. Key rotation and emergency revocation are implemented and tested. Revoked keys can no longer sign new decisions.

**Validation:** 37/37 key lifecycle tests.

**Limitation:** If an attacker obtains both the encrypted key and the decryption password (full system compromise), they can forge signatures. Physical security and access monitoring are the client's responsibility.

---

### Threat 7: Audit Log Modification or Deletion

**Description:** An attacker modifies or deletes historical audit log entries to hide evidence.

**Protection:** The audit log is append-only, with each entry cryptographically chained to its predecessor. Any modification breaks the chain. External copies can be stored for independent verification.

**Validation:** 43/43 chain integrity tests.

**Limitation:** Full-system compromise that allows simultaneous modification of all copies is outside UICP's protection scope.

---

### Threat 8: Unauthorized Access

**Description:** An unauthorized person reads constraint sets, audit logs, or personal data.

**Protection:** RBAC with three roles. Personal data is encrypted at rest (AES-256-GCM). All access attempts are logged. API authentication is required.

**Validation:** Access control tests confirm role boundaries. Encryption correctness validated by 35/35 personal data store tests.

**Limitation:** RBAC is enforced at the application layer. An attacker with root access to the host machine can bypass application-level controls. This is a deployment security responsibility.

---

## SECURITY CONTROLS BY PHASE

### Phase 1 (Normalization) Controls
- **Input validation:** Rejects malformed or oversized inputs before processing.
- **Deterministic canonicalization:** Eliminates Unicode tricks, whitespace ambiguities, and encoding exploits.
- **Fuzz-tested:** 10,368 adversarial inputs; zero bypasses.

### Phase 2 (Semantic Analysis) Controls
- **Schema validation:** Extraction schema is validated against the constraint set at load time.
- **Type checking:** Extracted bindings are type-checked; mismatches produce errors, not false ALLOWs.
- **Completeness check:** All variables referenced by constraints must be present in the extraction schema.

### Phase 3 (Satisfiability) Controls
- **Complete evaluation:** Every constraint is checked; none are skipped.
- **Complexity limits:** Maximum 256 constraints, 5-second computation timeout (configurable). Exceeding limits returns GATEWAY_UNAVAILABLE.
- **Deterministic:** Same bindings and constraints always produce the same result.

### Phase 4 (Enforcement) Controls
- **Fail-safe:** Errors in any prior phase produce GATEWAY_UNAVAILABLE, never ALLOW.
- **No probabilistic override:** Model confidence scores are ignored.
- **Decision logging:** Every decision is logged before Phase 5 signing.

### Phase 5 (Cryptographic Audit) Controls
- **Ed25519 signing:** Every decision is signed; signatures are mathematically unforgeable.
- **Append-only log:** Records cannot be deleted or modified without detection.
- **Hash chain:** Each record contains the hash of the previous record; tampering breaks the chain.
- **Encrypted personal data:** Personal data in logs is encrypted with AES-256-GCM.

---

## CRYPTOGRAPHIC FOUNDATIONS

UICP relies on three standard, well-audited cryptographic algorithms.

**Ed25519 (Signatures):** Provides 128-bit security. Signatures are 64 bytes; public keys are 32 bytes. Standardized in IETF RFC 8032. Chosen for speed, security, and resistance to implementation pitfalls.

**AES-256-GCM (Encryption):** Provides 256-bit security. Used to encrypt personal data at rest and the signing key on disk. Authenticated encryption mode (GCM) ensures both confidentiality and integrity.

**SHA-256 (Hashing):** Used for audit log hash chain and personal data hashing. 256-bit output. Collision-resistant and preimage-resistant under standard assumptions.

All three algorithms are implemented via the `cryptography` Python library — a widely audited, open-source package. UICP contains no custom cryptographic code.

---

## ACCESS CONTROL MODEL

UICP implements Role-Based Access Control (RBAC) with three roles:

**Gateway Role:** The enforcement process itself. Can execute Phases 1–4, read constraint sets, and create audit log entries. Cannot read encryption keys or modify constraints.

**Auditor Role:** Compliance officers and external auditors. Can read audit logs, verify signatures with public keys, and export decision records. Cannot modify constraints or access encryption keys.

**Operator Role:** System administrators. Can manage encryption keys (generate, rotate, revoke), update constraint sets, and configure system parameters. Cannot read audit logs or personal data.

Critical operations (key rotation, key revocation) require two-person authorization — two different operators must independently approve the action.

---

## DATA PROTECTION STRATEGY

**Encryption at rest:** Signing keys and personal data are encrypted with AES-256-GCM. Constraint sets and decision records (without personal data) are stored in plaintext for operational efficiency.

**Encryption in transit:** All API communication requires TLS/HTTPS.

**Data minimization:** Raw model outputs are not stored. Only extracted bindings are retained, and only for the configured retention period (default 30 days). After retention, raw values are deleted; cryptographic hashes remain for audit integrity.

**GDPR erasure:** Personal data can be deleted upon request while preserving audit trail integrity via hash pointers (validated by 35/35 personal data store tests).

---

## KEY MANAGEMENT: LIFECYCLE, ROTATION, AND REVOCATION

UICP implements a full key lifecycle manager (GAP-13/14, validated by 37/37 tests).

**Generation:** Keys are generated using cryptographically secure random number generators. Generated only by the Operator role; immediately encrypted before storage.

**Rotation:** Keys have a default validity period of 12 months. A new key is generated before expiry; old key is marked ROTATED. Historical signatures remain verifiable.

**Revocation:** If a key is compromised, it can be revoked immediately. Revoked keys cannot sign new decisions. All signatures from a revoked key are flagged as suspect.

**Emergency recovery:** Encrypted key backups are stored offline. Recovery requires two-person authorization.

---

## AUDIT AND MONITORING

Every enforcement decision is logged with: decision ID, timestamp, request ID, constraints checked, bindings evaluated, satisfiability result, enforcement decision, and Ed25519 signature.

Key management events (generation, rotation, revocation) and access events (RBAC checks) are also logged.

Monitored metrics include decision throughput, error rate, signature verification failures, key age, and resource usage. Alerts are triggered on threshold breaches.

---

## INCIDENT RESPONSE

If a security incident occurs (key compromise, audit log tampering, signature forgery):

1. **Containment (0–1 hour):** Revoke compromised key immediately. Switch UICP to manual enforcement until resolved. Notify affected clients.
2. **Investigation (1–24 hours):** Audit logs are reviewed. Root cause is determined.
3. **Recovery (24 hours–ongoing):** New key generated, system restored. Affected decisions are flagged.
4. **Post-incident review:** Full incident report, root cause analysis, preventive measures implemented.

---

## COMPLIANCE ALIGNMENT

UICP's security model is designed to align with:

- **EU AI Act Articles 6, 16, 82:** Auditable enforcement, transparency, and clear liability boundaries.
- **GDPR Articles 5, 17, 22, 32:** Data minimization, erasure rights, explanation capability, and technical security measures.
- **NIST AI RMF:** Govern, Measure, Manage functions.
- **ISO/IEC 27001 Annex A controls** for access control, encryption, logging, and incident response.

A detailed compliance mapping is provided in `docs/LEGAL_ASSESSMENT.md`.

---

## ASSUMPTIONS AND KNOWN LIMITATIONS

**Assumptions:**
- The cryptographic algorithms (Ed25519, AES-256, SHA-256) remain secure.
- The signing key is protected from physical theft and social engineering.
- The extraction schema and constraint set are correctly defined by the client.

**What UICP does NOT protect against (and does not claim to):**
- Incorrect or discriminatory constraint definitions (client responsibility).
- Incorrect extraction schemas (client responsibility).
- Social engineering or insider threats with legitimate access.
- Full system compromise (root access to the host).
- Physical attacks (side-channel, hardware key extraction).

**Current deployment limitations (to be addressed by Tier 1 gaps):**
- Single-process architecture; no automatic restart or failover.
- Single-tenant; no isolation between multiple clients.
- Constraint updates require service restart; no zero-downtime rotation.

These are openly documented and are the top-priority infrastructure items in the funded work plan.

---

## VERIFICATION PROCEDURES

Security claims can be independently verified using the following procedures (no access to source code required):

1. **Determinism:** Submit the same request 10 times; confirm identical signed output.
2. **Fail-safe:** Submit malformed input; confirm GATEWAY_UNAVAILABLE, not ALLOW.
3. **Signature validity:** Extract signature and decision data; verify with public key. Modify data; confirm verification fails.
4. **Audit log immutability:** Modify a historical audit log entry; confirm hash chain breaks.
5. **Key rotation:** Rotate signing key; confirm old signatures still verify, new signatures use new key.
6. **Access control:** Attempt operations outside assigned role; confirm denial and logging.

All procedures are documented in the public verification scripts available in the repository.

---

## CONCLUSION

UICP is a deterministic constraint enforcement system with a clear, honest security model. It protects against the specific threats that arise when AI model outputs must be checked against formal rules. It does not overclaim. Its limitations are documented. Its protections are empirically validated.

For security officers evaluating UICP for deployment, this document provides the information needed to assess risk. For auditors, it provides the verification procedures needed to independently confirm the system's behavior.

---

**END OF SECURITY MODEL**
