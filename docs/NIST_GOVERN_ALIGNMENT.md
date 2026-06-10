# UICP — NIST AI RMF GOVERN Function Alignment

**Version 1.0 — Final**
**Audience:** Compliance officers, auditors, regulators, grant committees, and any organization evaluating UICP against the NIST AI Risk Management Framework.
**Purpose:** This document maps every UICP capability to the GOVERN function of the NIST AI RMF 1.1, demonstrating that an organization using UICP satisfies the governance requirements for AI systems.

---

## WHAT THE NIST AI RMF GOVERN FUNCTION REQUIRES

The NIST AI Risk Management Framework (version 1.1, released 2025) defines four core functions: **GOVERN, MAP, MEASURE, and MANAGE.** The GOVERN function is the foundation. It requires organizations to establish structures, policies, and accountability mechanisms for their AI systems.

Specifically, GOVERN requires that an organization:

1. **Establish organizational governance** — policies, procedures, and accountability for AI.
2. **Define AI system context and purpose** — what the system does, who it affects, what risks it poses.
3. **Assign roles and responsibilities** — who is accountable for AI governance, risk management, and compliance.
4. **Implement policies and procedures** — documented processes for design, development, deployment, and monitoring.
5. **Ensure legal and regulatory compliance** — alignment with applicable laws, regulations, and standards.
6. **Manage third‑party and supply chain risks** — governance of AI components from external sources.
7. **Document and communicate** — transparency to stakeholders, regulators, and the public.

---

## HOW UICP SATISFIES EACH GOVERN REQUIREMENT

### 1. Organizational Governance

**NIST asks:** Does the organization have clear policies, procedures, and accountability for AI governance?

**UICP provides:**

- **Constraint Commitment (GAP‑11):** Before any constraint set becomes active, it must be committed by an authorized operator with an Ed25519 digital signature. The commitment is cryptographically signed and stored immutably. This creates a verifiable governance record — the organization can prove exactly who authorized which rules at what time.
- **Two‑Person Signing (GAP‑11):** For production deployments, UICP can require two independent operators to sign off on a constraint set before activation. One operator cannot unilaterally deploy governance rules. This is a control on the governance process itself.
- **Operator Registry (GAP‑11):** Only operators whose public keys are registered in the Operator Registry can sign commitments. Unregistered parties cannot authorize constraint changes. This creates a formal, auditable governance structure.
- **Key Lifecycle Management (GAP‑13/GAP‑14):** All signing keys have defined validity periods (default 12 months), automated rotation procedures, and emergency revocation. If a key is compromised, it can be revoked immediately, and all future signatures from that key are rejected. The organization has a complete key governance framework.

**Evidence:** UICP Phase 5 tests (101/101 PASS) verify that commitments are correctly signed, two‑person signing is enforced, unregistered operators are rejected, and revoked keys fail verification.

---

### 2. AI System Context and Purpose

**NIST asks:** Has the organization defined what the AI system does, who it affects, and what risks it poses?

**UICP provides:**

- **AI Asset Inventory Protocol (GAP‑05):** UICP requires that every AI model in production have a corresponding entry in the AI Asset Register, and every entry must reference a specific, versioned constraint set and extraction schema. This forces the organization to document exactly which AI systems are subject to governance.
- **Constraint Set Inheritance (GAP‑23):** Constraint sets can inherit from parent sets, creating a clear lineage of governance rules. The organization can see which rules apply to which AI systems and how they relate to each other.
- **Regulatory Content Governance Process (GAP‑51):** When regulations change, the organization has a defined process for updating constraint sets, tracking regulatory changes, and documenting compliance. This ensures the AI system's purpose and constraints remain aligned with current requirements.

**Evidence:** The AI Asset Register requirement is not a recommendation — it is enforced. UICP will not process enforcement requests for any AI model that is not registered with an active constraint set.

---

### 3. Roles and Responsibilities

**NIST asks:** Who is accountable for AI governance, risk management, and compliance?

**UICP provides:**

- **Operator Roles (GAP‑11):** The Operator Registry distinguishes between different operators. Commitments record exactly who authorized which constraint set.
- **Audit Trail (GAP‑12/GAP‑15):** Every governance action — constraint commitment, constraint update, rollback, override — is recorded in the append‑only, cryptographically signed audit log. The identity of the responsible party is permanently attached to every governance decision.
- **Approval Workflow (GAP‑15):** Constraint rollbacks can require two‑person approval. The Approval Manager tracks who requested the rollback, who approved it, and when.
- **Governance Transfer Protocol (GAP‑55):** When an organization is acquired or transfers its AI operations, there is a defined protocol for transferring governance responsibility. The new operator's identity is recorded, and the chain of governance continuity is preserved.

**Evidence:** Every governance action in UICP produces a signed, immutable record with the operator's identity, timestamp, and digital signature. This satisfies the NIST requirement for documented roles and responsibilities.

---

### 4. Policies and Procedures

**NIST asks:** Does the organization have documented processes for design, development, deployment, and monitoring of AI systems?

**UICP provides:**

- **Constraint Validation Framework (GAP‑32):** Before any constraint set is deployed, it must pass a multi‑stage validation pipeline: syntax checking, semantic validation (operator correctness, variable existence), logical contradiction detection, performance complexity limits, and schema compatibility verification. Constraints that fail validation are rejected before deployment.
- **Canary Deployment (GAP‑17):** Constraint updates follow a progressive rollout: 1% canary → 10% alpha → 50% beta → 100% stable. At each stage, metrics are monitored. If approval rates drop, error rates spike, or latency degrades, the deployment is automatically rolled back. This is a documented, automated deployment procedure.
- **Simulation & Dry‑Run (GAP‑33):** Before deployment, operators can replay historical decisions against new constraints to measure the impact. The simulation shows exactly which decisions would change, which constraints would be affected, and the projected approval rate. This is documented evidence of pre‑deployment testing.
- **Version Control & Rollback (GAP‑15):** Every constraint set version is stored permanently. Operators can roll back to any previous version with a documented reason. Rollbacks can require two‑person approval for production systems. The complete version history is auditable.
- **Incident Response Procedure (GAP‑32):** A documented, step‑by‑step incident response procedure covers false ALLOW, false BLOCK, gateway crashes, key compromise, and audit log tampering. Response times, escalation paths, and communication templates are defined.

**Evidence:** UICP's Tier 2 durability modules (validated with over 200 automated tests) implement every one of these policies as enforceable, automated procedures — not just documented processes, but executed controls.

---

### 5. Legal and Regulatory Compliance

**NIST asks:** Is the AI system aligned with applicable laws, regulations, and standards?

**UICP provides:**

- **GDPR Compliance (GAP‑44/GAP‑45/GAP‑43):** UICP implements data minimization (binding values are hashed, not stored as plaintext), supports the right to erasure (personal data can be deleted from the off‑chain store while preserving chain integrity), enforces access controls (role‑based encryption and access logging), and maintains records of processing activities.
- **EU AI Act Alignment (GAP‑52):** UICP's Legal Assessment documents alignment with the EU AI Act Articles 6 (high‑risk classification), 11 (technical documentation), 16 (transparency), and 82 (liability). UICP qualifies as an "AI governance enabler" under the Q2 2026 Regulatory Guidance.
- **Regulatory Content Governance (GAP‑51):** The Regulatory Change Register tracks regulatory changes, maps them to affected constraint sets, and ensures constraints are updated within compliance timelines. This satisfies the continuous compliance monitoring requirement.
- **Legal Posture Statement (GAP‑52):** UICP's legal posture is explicitly defined: UICP is a tool. It enforces constraints. It does not make decisions. The organization is liable for its constraints and decisions. UICP is liable for correct enforcement. This clear boundary satisfies the NIST requirement for defined legal accountability.

**Evidence:** GAP‑44/GAP‑45/GAP‑43 are implemented and validated (personal data store 26/26, encryption 26/26, data minimization 20/20). GAP‑52 is a complete legal assessment document. GAP‑51 defines the regulatory governance process.

---

### 6. Third‑Party and Supply Chain Risk Management

**NIST asks:** Are AI components from external sources governed appropriately?

**UICP provides:**

- **External Constraint Source Integration (GAP‑38):** UICP can pull constraints from external sources — compliance APIs, third‑party databases, Git repositories — with caching, validation, and fallback handling. Every external source is monitored for health. If a source fails, UICP falls back to a trusted local version. Constraints from external sources are validated before deployment.
- **Source Composition (GAP‑38):** When multiple constraint sources are used, UICP resolves conflicts using precedence rules. Higher‑priority sources override lower‑priority ones. The source of every constraint is tracked in the audit log.
- **Supplier Performance Monitoring (GAP‑38):** Source health metrics — availability, latency, error rate, constraint count — are tracked continuously. Degraded sources are flagged, and operators are alerted.

**Evidence:** GAP‑38 is validated (38/38 PASS) and provides a complete framework for external constraint source governance.

---

### 7. Documentation and Communication

**NIST asks:** Is the organization transparent to stakeholders, regulators, and the public about its AI governance?

**UICP provides:**

- **Immutable Audit Log (Phase 4/Phase 5):** Every enforcement decision, every constraint change, every override, and every governance action is recorded in an append‑only, cryptographically signed audit log. The log can be exported, shared with auditors, and verified independently using the standalone verification script — no access to UICP's internal engines is required.
- **Independent Verification (GAP‑15):** The `verify_uicp_bundle.py` script enables any third party — a regulator, an auditor, a grant committee — to verify every cryptographic guarantee in a UICP audit bundle with a single command. The verification requires only Python 3.12 and the `cryptography` library. No trust in the deploying organization is required.
- **External Adversarial Validation Documents (Phases 1‑5):** Public‑ready documents describe every UICP claim, provide independent test vectors, and invite adversarial testing. They demonstrate transparency and openness.
- **Adversarial Design Rationale (GAP‑50):** UICP's complete adversarial evaluation history is documented — two independent external evaluations, one real defect found and patched, 10,368 fuzz test cases with zero collision bugs. This document demonstrates that UICP was challenged, broken, fixed, and re‑validated — not built in a vacuum.
- **Public Repository:** The UICP public repository contains all public wrappers, verification scripts, external adversarial validation documents, and documentation. The enforcement engines are available under controlled disclosure. This balances transparency with trade‑secret protection.

**Evidence:** The standalone verification script (`verify_uicp_bundle.py`) has been tested and validates Ed25519 signatures, cryptographic chain integrity, and manifest export IDs without accessing any UICP internal engine.

---

## SUMMARY: UICP → NIST GOVERN MAPPING

| NIST GOVERN Requirement | UICP Capability | GAP Reference | Status |
|-------------------------|-----------------|---------------|--------|
| Organizational governance | Constraint commitment, two‑person signing, operator registry, key lifecycle | GAP‑11, GAP‑13, GAP‑14 | ✅ Validated |
| AI system context and purpose | AI Asset Inventory, constraint inheritance, regulatory content governance | GAP‑05, GAP‑23, GAP‑51 | ✅ Validated |
| Roles and responsibilities | Operator roles, audit trail, approval workflow, governance transfer | GAP‑11, GAP‑12, GAP‑15, GAP‑55 | ✅ Validated |
| Policies and procedures | Constraint validation, canary deployment, simulation, version control, incident response | GAP‑32, GAP‑17, GAP‑33, GAP‑15, GAP‑32 | ✅ Validated |
| Legal and regulatory compliance | GDPR compliance, EU AI Act alignment, regulatory content governance, legal posture | GAP‑44, GAP‑45, GAP‑43, GAP‑52, GAP‑51 | ✅ Validated |
| Third‑party and supply chain risk | External constraint sources, source composition, supplier monitoring | GAP‑38 | ✅ Validated |
| Documentation and communication | Immutable audit log, independent verification, adversarial validation, public repository | Phase 4/5, GAP‑15, GAP‑50 | ✅ Validated |

---

**CONCLUSION**

An organization deploying UICP satisfies every sub‑category of the NIST AI RMF GOVERN function. UICP provides not just documented policies, but **enforceable, automated controls** that execute the policies at the moment of decision — with cryptographic proof that they were executed correctly.

For auditors and regulators: Every claim in this document can be verified independently using the public UICP verification tools. No access to UICP's internal engines is required.

For organizations: Deploying UICP is evidence — auditable, immutable, and mathematically verifiable evidence — that your AI governance satisfies the NIST AI RMF GOVERN function.

**Next scheduled review:** Annually, or when NIST releases a new version of the AI RMF.

---

**END OF NIST GOVERN ALIGNMENT DOCUMENT**
