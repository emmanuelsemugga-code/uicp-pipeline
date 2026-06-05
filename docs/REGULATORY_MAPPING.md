# UICP Regulatory Mapping

## Version 2.0 — Pilot‑Ready
### Status: Aligned with Validated Architecture (GAP‑28), Security Model (GAP‑29), and Legal Assessment (GAP‑52)
### Audience: Compliance Officers, Regulators, Auditors, Procurement Teams
### Purpose: To map UICP’s empirically validated capabilities to the requirements of major AI governance and data protection frameworks — without exposing internal algorithms or enabling replication.

---

## HOW TO USE THIS DOCUMENT

This document is a **compliance reference**, not a legal warranty. For each regulatory requirement listed, we state:

1. **What the regulation demands** (the obligation).
2. **What UICP demonstrably does** (the capability, backed by test evidence).
3. **What the deploying organisation must do itself** (the client’s residual responsibility).
4. **Where to find the evidence** (pointer to the relevant specification or test suite).

Where UICP cannot satisfy a requirement, that is stated explicitly. No capability is claimed unless it has been validated by the automated test suites and external adversarial evaluations recorded in the Architecture Specification (GAP‑28) and Security Model (GAP‑29).

---

## REGULATORY LANDSCAPE — UICP’S POSITION

UICP is a **deterministic constraint‑enforcement gateway**. It sits between an AI model and the world, checking every model output against formal rules before that output can be acted upon. It does not make decisions. It does not judge intent. It applies logic.

Because UICP is external to the model and fully auditable, it occupies a unique regulatory position: **it is an AI governance enabler**, not a high‑risk AI system in itself. This distinction is recognised in the EU Regulatory Guidance of Q2 2026 and is consistent with the NIST AI RMF’s treatment of “safety‑critical software components.”

The mapping below shows how UICP’s capabilities align with the major frameworks without over‑claiming. Every capability listed is backed by the validated test suites described in the Architecture Specification.

---

## EU AI ACT (Regulation 2024/1689)

### Article 6 — High‑Risk AI System Classification

**What the regulation requires:**  
High‑risk AI systems must be auditable, supported by governance documentation, and accompanied by technical testing logs that prove correct behaviour.

**What UICP demonstrably provides:**

- **Auditability:** Every enforcement decision is cryptographically signed (Ed25519). The complete reasoning trail — constraints checked, bindings evaluated, satisfiability result, and final decision — is recorded in an append‑only, tamper‑evident audit log. The log can be verified by any third party holding the public key, without access to UICP’s internal engines.
- **Governance documentation:** The Architecture Specification, this Regulatory Mapping, the Security Model, and the Legal Assessment together form the governance record.
- **Technical testing logs:** The Phase 4 enforcement engine has passed 73 automated tests; the Phase 5 audit engine has passed 101 tests; the REST API has passed 14 integration tests; and 10 368 adversarial constraint sets have been fuzz‑tested with zero collision bugs. All test suites are re‑runnable.

**What the deploying organisation must do:**  
Classify its own AI system under Article 6. UICP is a component; the overall system classification depends on the use case and the constraints registered. The organisation must maintain the governance documentation and make it available to the relevant notified body.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` (test evidence and audit trail design)  
- `docs/SECURITY_MODEL.md` (cryptographic signing and chain integrity)

---

### Article 16 — Transparency Obligations

**What the regulation requires:**  
Users of high‑risk AI systems must be informed that an AI system is involved in a decision, and must receive information about the system’s capabilities and limitations.

**What UICP demonstrably provides:**

- Every enforcement decision includes a machine‑readable record of the constraints that were checked and the bindings that were evaluated. This record can be translated into a plain‑language explanation (e.g., “Your application was blocked because the constraint ‘age >= 18’ was violated. The recorded age was 16.”).
- A disclosure template is provided in the Operator Manual for clients to customise.

**What the deploying organisation must do:**  
Integrate the decision record into its customer‑facing disclosure process. The organisation is responsible for the accuracy and completeness of the plain‑language explanation.

**Evidence location:**  
- Operator Manual (GAP‑31, pending) — disclosure template  
- `docs/LEGAL_ASSESSMENT.md` — transparency posture

---

### Article 82 — Liability

**What the regulation requires:**  
If an AI system causes harm, the provider is presumed liable unless it can prove the harm did not originate from the system.

**What UICP demonstrably provides:**

- Cryptographic signatures and deterministic replay enable the provider to prove exactly which constraints were checked and what decision was made. This evidence can be submitted in any legal or regulatory proceeding.
- UICP operates under the **Tool Provider** legal posture: the provider warrants that the enforcement engine works as documented; the client warrants that the constraints and extraction schema are correct. This separation of liability is documented in the Legal Assessment.

**What the deploying organisation must do:**  
Maintain the audit trail and be prepared to produce it in response to a challenge. Obtain appropriate professional indemnity or cyber insurance.

**Evidence location:**  
- `docs/LEGAL_ASSESSMENT.md` — full liability analysis  
- `docs/SECURITY_MODEL.md` — signature verification procedure
- ## NIST AI RISK MANAGEMENT FRAMEWORK (v1.1)

The NIST AI RMF organises risk management into four functions: **Govern, Map, Measure, Manage**.

### Govern

**What the framework expects:**  
Organisations must establish governance structures, define risk tolerance, and allocate accountability.

**What UICP demonstrably provides:**

- Role‑based access control (gateway, auditor, operator) enforces separation of duties.  
- Dual‑operator constraint commitment (GAP‑11) requires two independent approvals before a constraint set becomes active.  
- Key lifecycle management (GAP‑13/14) ensures signing keys are rotated before expiry and can be revoked in an emergency.

**What the deploying organisation must do:**  
Define its risk tolerance in the form of specific constraints. Assign individuals to the UICP roles and maintain the operator registry.

**Evidence location:**  
- `docs/SECURITY_MODEL.md` — RBAC and key lifecycle  
- `docs/LEGAL_ASSESSMENT.md` — governance posture

---

### Map

**What the framework expects:**  
Organisations must understand their AI system’s components, data flows, and context.

**What UICP demonstrably provides:**

- The five‑phase pipeline is documented in the Architecture Specification with clear input/output contracts for each phase.  
- Data flows are traceable: model output → extracted bindings → constraint evaluation → enforcement decision → signed audit record.

**What the deploying organisation must do:**  
Document the AI model that feeds UICP, the extraction schema used, and the downstream systems that consume the enforcement decision. UICP does not discover or inventory AI assets.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` — data flow description

---

### Measure

**What the framework expects:**  
Organisations must test their AI systems and measure behaviour against risk targets.

**What UICP demonstrably provides:**

- Deterministic enforcement: identical inputs always produce identical outputs (validated by 73 enforcement tests, 101 audit tests, and 14 API tests).  
- Constraint evaluation correctness: 10 368 adversarial constraint sets tested with zero collision bugs.  
- Adversarial robustness: two independent external evaluations conducted; one real defect found and patched; one challenge withdrawn after technical review.  
- Every decision is logged with full reasoning, enabling quantitative measurement of violation rates, error rates, and decision volumes.

**What the deploying organisation must do:**  
Define quantitative risk targets (e.g., acceptable false‑positive rate), run the public verification scripts to independently confirm UICP’s determinism, and monitor the audit logs continuously.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` — test evidence and verification procedures  
- Public verification scripts in the repository

---

### Manage

**What the framework expects:**  
Organisations must implement controls to mitigate identified risks and respond to incidents.

**What UICP demonstrably provides:**

- Fail‑safe semantics: any internal error produces GATEWAY_UNAVAILABLE (a structured BLOCK), never a silent ALLOW.  
- Encryption at rest (AES‑256‑GCM) and in transit (TLS).  
- Immutable audit log with cryptographic chain integrity.  
- Documented incident‑response commitments (48‑hour patch for security defects, 72‑hour patch for critical enforcement defects).

**What the deploying organisation must do:**  
Implement the incident‑response procedures, monitor the audit log for anomalies, and conduct periodic security reviews of the deployment environment.

**Evidence location:**  
- `docs/SECURITY_MODEL.md` — full threat model and controls  
- `docs/LEGAL_ASSESSMENT.md` — incident‑response commitments

---

## GDPR (Regulation 2016/679)

UICP processes personal data when extracting bindings from model outputs. The following Articles are directly relevant.

### Article 5 — Data Protection Principles

**What the regulation requires:**  
Personal data must be processed lawfully, fairly, transparently, for specified purposes, minimised, accurate, retained no longer than necessary, and kept secure.

**What UICP demonstrably provides:**

- **Lawful basis:** Processing is performed under the client’s legitimate interest in enforcing governance constraints, or under consent if the client configures it.  
- **Purpose limitation:** Data is used exclusively for constraint enforcement and audit trail maintenance.  
- **Data minimisation:** Raw model outputs are never stored. Only extracted bindings are retained, and only for a configurable retention period (default 30 days). After retention, raw values are deleted; cryptographic hashes remain for audit integrity.  
- **Accuracy:** Bindings are extracted deterministically according to the client‑defined schema. UICP never modifies extracted values.  
- **Storage limitation:** Default 30‑day retention; configurable by the client.  
- **Security:** AES‑256‑GCM encryption at rest; Ed25519 signing; role‑based access control; append‑only audit log.

**What the deploying organisation must do:**  
Configure the retention period, define the lawful basis for processing, and ensure the extraction schema is accurate.

**Evidence location:**  
- GAP‑44 test suite (GDPR erasure architecture, 26 tests)  
- GAP‑45 test suite (encrypted personal data store, 26 tests)  
- `docs/SECURITY_MODEL.md` — encryption and access control

---

### Article 17 — Right to Erasure

**What the regulation requires:**  
Data subjects may request deletion of their personal data. The controller must comply within 30 days.

**What UICP demonstrably provides:**

- Raw personal data (bindings) are stored off‑chain in an encrypted PersonalDataStore. Erasure deletes the raw value while preserving the cryptographic hash in the audit log. This enables erasure without breaking audit‑trail integrity.  
- The erasure operation is cryptographically logged, producing a verifiable record that the data was deleted while the enforcement decision remains provable.

**What the deploying organisation must do:**  
Verify the data subject’s identity, check for legal holds, and issue the erasure request to UICP. UICP does not decide whether erasure is legally required.

**Evidence location:**  
- GAP‑44 test suite (26 tests)  
- `docs/LEGAL_ASSESSMENT.md` — erasure procedure

---

### Article 32 — Security of Processing

**What the regulation requires:**  
Appropriate technical and organisational measures to secure personal data.

**What UICP demonstrably provides:**

- Encryption at rest (AES‑256‑GCM) and in transit (TLS).  
- Ed25519 signatures on all enforcement decisions — mathematically unforgeable under standard assumptions.  
- Role‑based access control (gateway, auditor, operator).  
- Append‑only, cryptographically chained audit log; any tampering is immediately detectable.  
- Key lifecycle management: keys have defined validity periods (default 12 months), can be rotated, and can be revoked in an emergency.

**What the deploying organisation must do:**  
Secure the deployment environment (operating system, network, physical access). UICP’s application‑layer controls cannot protect against a compromised host.

**Evidence location:**  
- `docs/SECURITY_MODEL.md` — full control catalogue

---

### Article 35 — Data Protection Impact Assessment

**What the regulation requires:**  
A DPIA must be conducted for high‑risk processing.

**What UICP demonstrably provides:**

- The Architecture Specification and Security Model provide the necessary technical input for a DPIA: data flows, threat model, residual risks.  
- The audit log and personal‑data store are designed so that the DPIA can reference specific, testable controls rather than vague assurances.

**What the deploying organisation must do:**  
Conduct the DPIA itself. UICP provides evidence; the organisation owns the assessment and any required consultation with the supervisory authority.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` — data flows  
- `docs/SECURITY_MODEL.md` — threat model  
- `docs/LEGAL_ASSESSMENT.md` — risk register

---

## HEALTHCARE: FDA GUIDANCE ON AI/ML IN MEDICAL DEVICES

The FDA’s proposed framework for AI/ML‑based software as a medical device emphasises “effective monitoring strategies” and “failure mode analysis.”

**What the FDA expects:**

- Algorithm documentation, transparency, bias testing, and failure‑mode analysis.

**What UICP demonstrably provides:**

- **Algorithm documentation:** The constraint set is the algorithm. Every constraint is human‑readable and its enforcement is deterministic.  
- **Transparency:** Signed decision records prove what was checked.  
- **Bias testing:** Constraints can explicitly encode fairness requirements; audit logs enable retrospective disparate‑impact analysis.  
- **Failure‑mode analysis:** Fail‑safe defaults (GATEWAY_UNAVAILABLE) and comprehensive testing (58 fail‑safe tests) demonstrate that the system fails safely.

**What the deploying organisation must do:**  
Define clinically‑validated constraints, test them against historical patient data, and submit the constraint set as part of the device’s algorithm documentation. UICP does not validate the clinical correctness of the constraints.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` — pipeline description and test evidence  
- `docs/SECURITY_MODEL.md` — fail‑safe behaviour

---

## FINANCIAL SERVICES: FAIR LENDING AND AML

### Equal Credit Opportunity Act (ECOA) / Fair Housing Act (FHA)

**What the regulation requires:**  
Lending decisions must not discriminate based on protected characteristics.

**What UICP demonstrably provides:**

- Constraints can encode non‑discrimination rules. A constraint such as “IF applicant.age < 18 THEN BLOCK” is enforced deterministically.  
- Audit logs enable regulators to verify that no protected‑class applicant was treated differently under identical constraint evaluation.

**What the deploying organisation must do:**  
Define the constraints that operationalise fair‑lending requirements. UICP enforces whatever constraints it is given; it cannot detect whether a constraint set is discriminatory.

**Evidence location:**  
- `docs/LEGAL_ASSESSMENT.md` — constraint‑definition liability

### AML/CFT (FinCEN, FATF)

**What the regulation requires:**  
Financial institutions must screen transactions against sanctions lists and report suspicious activity.

**What UICP demonstrably provides:**

- A constraint such as “IF transaction.beneficiary IN sanctions_list THEN BLOCK” is evaluated deterministically for every transaction.  
- The audit log proves that the check was performed.

**What the deploying organisation must do:**  
Maintain the sanctions list and update the constraint when the list changes. UICP does not source the list.

**Evidence location:**  
- `docs/ARCHITECTURE_SPECIFICATION.md` — constraint evaluation
- ## CROSS‑JURISDICTIONAL APPLICABILITY

UICP is infrastructure. It can be deployed in any jurisdiction because:

- **Constraint sets are client‑defined.** The rules enforced are whatever the client registers. UICP itself contains no jurisdiction‑specific logic.  
- **The audit trail is portable.** Signed JSON records can be verified by any third party with the public key, regardless of where the system is hosted.  
- **Data residency is configurable.** The Docker container can run on‑premises, in a national cloud region, or in a hybrid environment. UICP imposes no data‑transfer requirement.  
- **The legal posture is jurisdiction‑neutral.** The Tool Provider model assigns liability for constraint correctness to the client, while the provider warrants the enforcement engine. This posture is compatible with EU, US, UK, and other major liability frameworks.

Specific jurisdictional notes are provided in the Legal Assessment (`docs/LEGAL_ASSESSMENT.md`). This document does not duplicate them.

---

## WHAT UICP DOES NOT COVER (HONEST BOUNDARIES)

Every compliance claim above is bounded by these explicit limitations. No capability is implied beyond what is listed.

- **Constraint definition:** UICP enforces constraints; it does not write them. If a constraint is missing, incomplete, or discriminatory, UICP will faithfully enforce it. The ethical and legal responsibility for constraint content lies with the deploying organisation.  
- **Extraction schema correctness:** UICP extracts bindings according to the schema the client provides. If the schema is wrong, the bindings will be wrong, and UICP will enforce constraints on incorrect data. The client is responsible for schema accuracy.  
- **Model behaviour:** UICP does not control the AI model that produces the outputs it checks. It cannot prevent a model from generating harmful text that does not violate a numeric constraint. Semantic harms, qualitative bias, and prompt‑injection attacks that produce false bindings are outside UICP’s enforcement scope.  
- **Truth verification:** UICP does not independently verify whether extracted bindings reflect reality. It enforces constraints on the values it receives. If a trusted source is registered via the TrustedSourceRegistry, mismatches are detected; otherwise, UICP trusts the bindings it extracts.  
- **Physical and host security:** UICP’s application‑layer controls cannot protect against a compromised operating system, physical theft, or side‑channel attacks.  
- **Regulatory classification:** UICP does not automatically classify an AI system under the EU AI Act, FDA rules, or any other framework. That classification is the client’s responsibility.

---

## EVIDENCE INDEX

All claims in this document are traceable to specific, re‑runnable test suites. The table below provides a quick reference.

| Claim | Evidence | Test Count |
|-------|----------|------------|
| Deterministic enforcement | Phase 4 engine test suite | 73/73 |
| Cryptographic signing | Phase 5 audit engine test suite | 101/101 |
| REST API correctness | Integration test suite | 14/14 |
| Constraint evaluation correctness | Fuzz harness | 10 368 constraint sets, zero bugs |
| Fail‑safe behaviour | GAP‑21 test suite | 58/58 |
| GDPR erasure | GAP‑44 test suite | 26/26 |
| Encrypted personal data store | GAP‑45 test suite | 26/26 |
| Key lifecycle (rotation/revocation) | GAP‑13/14 test suite | 37/37 |
| Two‑person signing | GAP‑11 test suite | 21/21 |
| External adversarial evaluation | Two independent reviews | 1 defect found & patched; 1 challenge withdrawn |

All test suites are embedded in the engine files and can be executed with `python3 <engine_file>.py`. Public verification scripts that exercise the public wrappers are also available.

---

## RELATIONSHIP TO OTHER DOCUMENTS

This document is part of a set. Readers should also consult:

- **Architecture Specification (`docs/ARCHITECTURE_SPECIFICATION.md`):** Describes the five‑phase pipeline, data flows, and design rationale.  
- **Security Model (`docs/SECURITY_MODEL.md`):** Defines the threat model, cryptographic assumptions, access controls, and incident‑response commitments.  
- **Legal Assessment (`docs/LEGAL_ASSESSMENT.md`):** Establishes the Tool Provider legal posture, warranty and disclaimer language, and liability boundaries.  
- **Operator Manual (GAP‑31, pending):** Provides step‑by‑step deployment and operational procedures, including the Article 16 disclosure template.  
- **Grant Evidence Pack (`docs/GRANT_EVIDENCE_PACK.md`):** Summarises the problem, solution, and evidence for non‑technical audiences.

No single document should be read in isolation. Together they form the complete governance record for a UICP deployment.

---

## DOCUMENT CONTROL

- **Version:** 2.0  
- **Date:** June 2026  
- **Status:** Pilot‑Ready (15 critical gaps closed; 3 launch gaps remaining)  
- **Maintained by:** UICP development team  
- **Review cadence:** This document must be reviewed whenever a new regulatory framework is added, an existing framework is amended, or a new capability is validated that affects a compliance claim.

---

**END OF REGULATORY MAPPING**
- 
