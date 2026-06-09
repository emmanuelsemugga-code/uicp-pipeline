# UICP Adversarial Design Rationale

## Version 1.0 — Final
### Status: Active
### Audience: Grant Committees, Regulators, Security Auditors, Technical Evaluators

---

## 1. PURPOSE

This document records the adversarial evaluation history of UICP — who tested it, what they found, what we fixed, and what we learned. It exists because:

- **Grant committees** require evidence that a system has been independently tested.
- **Regulators** require evidence that a system's claims have been challenged and validated.
- **Security auditors** require a record of prior vulnerabilities and their remediation.
- **Future maintainers** require an understanding of why the system is designed the way it is.

UICP was not built in isolation. It was subjected to external adversarial scrutiny. This document is the proof.

---

## 2. EVALUATION HISTORY

### 2.1 First External Adversarial Evaluation (2025)

**Evaluator:** Independent AI safety researcher (name withheld by request)
**Scope:** Phase 1 — Constraint Normalization Engine
**Duration:** 2 weeks
**Methodology:** The evaluator was given access to the public NORMALIZE interface and the adversarial claim register. They were asked to find any input within the defined DSL and admission limits that would cause non‑deterministic output, unbounded growth, or incorrect normalization.

#### Finding 1: Missing Node‑Count Limit Enforcement

**Description:** The evaluator constructed a constraint set with 300 AND‑linked terms producing 901 Abstract Syntax Tree (AST) nodes. The admission gate correctly enforced the constraint count limit (K=16), the depth limit (D=32), and the variable count limit (V=64). However, it did not enforce the total AST node limit (N_MAX=256). The output contained 901 nodes — nearly four times the documented limit.

**Severity:** CRITICAL — a documented guarantee was not enforced.

**Root cause:** The N_MAX constant was declared in the specification but was absent from the ADMIT function's validation logic. All other limits were enforced; this one was overlooked.

**Remediation:** The node‑count check was added to the NORMALIZE function after the dominance‑reduction step. This ensures that inputs which collapse to a small output (e.g., 16 identical bounds → 1 node) are correctly accepted, while genuinely oversized outputs are rejected.

**Verification:** The test suite was expanded to include node‑count boundary tests. All 26/26 Phase 1 tests now pass, including the specific adversarial input that triggered the finding.

**Design lesson:** Every documented constant must have a corresponding enforcement check. Specification‑code mismatches are the most common class of vulnerability in deterministic systems.

---

### 2.2 Second External Adversarial Evaluation (2026)

**Evaluator:** Independent software security researcher (name withheld by request)
**Scope:** Phase 1 — Determinism Guarantee
**Duration:** 1 week
**Methodology:** The evaluator attempted to construct inputs that would cause the canonical_transform function to produce non‑deterministic output or crash.

#### Finding 2: Division‑by‑Zero Challenge (WITHDRAWN)

**Description:** The evaluator claimed that the determinism guarantee was broken because the internal canonical_transform function could raise an uncaught ValueError when evaluating a constraint containing division‑by‑zero (e.g., "x > (5/0)").

**Evaluator's claim:** "If canonical_transform can crash on some inputs, then the determinism guarantee is false — the system does not always produce an output."

**Our response:** The determinism guarantee applies to the public NORMALIZE interface, not to the internal canonical_transform helper. The NORMALIZE function wraps canonical_transform in exception handling. Any internal error — including division‑by‑zero — produces a deterministic REJECT+HALT result, not a crash and not non‑deterministic output.

**Outcome:** The evaluator reviewed the NORMALIZE implementation, confirmed that all exceptions are caught and handled deterministically, and withdrew the challenge in full.

**Design lesson:** The distinction between "internal function determinism" and "public interface determinism" must be clearly documented. The public guarantee is what matters for downstream consumers; internal functions may fail safely as long as the public interface handles those failures deterministically.

---

### 2.3 Internal Fuzz Testing (2025‑2026)

**Methodology:** A fuzz harness was built to generate random constraint sets within the admission limits and verify that:
- Normalization is deterministic (same input → same output across 10 runs).
- Normalization is idempotent (normalizing twice produces identical output).
- Normalization terminates (no infinite loops).
- Output respects all structural bounds (node count, depth, variable count).

**Scale:** 10,368 unique constraint sets were generated and tested.

**Results:** Zero genuine collision bugs found. One defect was identified during fuzz‑test development (the node‑count limit gap, which was patched before the fuzz harness was finalised).

---

## 3. DESIGN DECISIONS DRIVEN BY ADVERSARIAL TESTING

Several architectural decisions in UICP were directly shaped by the adversarial evaluation process.

### 3.1 Pipeline Order Locking

**What:** The six‑step normalization pipeline (constant_fold → algebraic_simplify → relational_normalize → boolean_flatten → boolean_simplify → operand_sort) is locked and must never be reordered.

**Why:** During development, a two‑pass convergence bug was discovered: boolean_simplify could not absorb "A OR (A AND B AND C)" until boolean_flatten had first produced the n‑ary AND form. Reversing the order of these two steps produced incorrect normalization. The pipeline order is now enforced by design — no function may call a step out of sequence.

**Adversarial relevance:** An attacker who could reorder the pipeline (e.g., through a configuration injection) could cause constraints to be normalized incorrectly, potentially allowing violations to pass undetected. Locking the pipeline eliminates this attack vector.

### 3.2 Fail‑Safe Defaults

**What:** UICP defaults to BLOCK and manual review when it encounters an error it cannot safely recover from. It never defaults to ALLOW.

**Why:** The adversarial evaluation process emphasised that a constraint enforcement system that silently allows violations during error conditions is worse than no system at all — it creates false confidence. The fail‑safe design ensures that errors are always visible and always require human intervention.

**Adversarial relevance:** An attacker who can trigger an error condition (e.g., malformed input, resource exhaustion) cannot use that error to bypass constraints. The system blocks by default, requiring manual override.

### 3.3 Append‑Only Audit Log with Cryptographic Chaining

**What:** The audit log is append‑only. Each entry contains a cryptographic hash of the previous entry. Any modification to a historical record breaks the chain and is immediately detectable.

**Why:** During adversarial evaluation, a hypothetical attack was identified: an insider with database access could modify a historical BLOCK decision to ALLOW, hiding a violation. The append‑only design with cryptographic chaining makes this attack detectable — the modified record's hash will not match the next record's chain reference.

**Adversarial relevance:** This design ensures that even if an attacker gains write access to the audit database, they cannot silently modify historical decisions. Tampering is always detectable.

### 3.4 Ed25519 Signatures on Every Decision

**What:** Every enforcement decision is cryptographically signed using Ed25519. The signature covers the decision, the constraints checked, and the bindings evaluated.

**Why:** A related hypothetical attack was identified: an attacker could inject a fabricated decision record into the audit log, claiming UICP made a decision it never actually made. Because Phase 5 only signs decisions produced by Phase 4, a fabricated record would lack a valid signature and would be rejected during verification.

**Adversarial relevance:** The Ed25519 signature provides non‑repudiation. UICP can prove what it decided and when. A fabricated decision cannot carry a valid signature without the private key.

---

## 4. KNOWN LIMITATIONS AND ACCEPTED RISKS

UICP's adversarial testing did not identify every possible vulnerability. The following limitations are acknowledged and accepted:

### 4.1 Prompt Injection in Binding Extraction

**What:** The binding extraction layer uses regex patterns to extract numeric values from model outputs. An attacker who knows the extraction schema can craft a model output that contains false binding values designed to satisfy constraints.

**Status:** Accepted risk. UICP enforces constraints on the bindings it receives; it does not independently verify the truth of those bindings. The TrustedSourceRegistry (GAP‑36) provides optional cross‑referencing with authoritative data sources, but full protection against prompt injection requires external truth‑verification systems.

**Mitigation:** Clients are advised to use constant bindings or TrustedSourceRegistry for critical variables.

### 4.2 Canonicalization Correctness Over Full Grammar Space

**What:** The constraint normalization pipeline has been tested against known edge cases (operator flipping, constant folding, algebraic simplification, absorption, commutativity) but has not been formally proven correct over the full constraint grammar space.

**Status:** Accepted risk. Formal verification of the full grammar would require academic‑level proof engineering. The empirical test suite (26/26 Phase 1, 73/73 Phase 4, 101/101 Phase 5, 10,368 fuzz cases) provides strong evidence of correctness. A bug that causes two semantically different constraints to produce the same canonical form remains possible but has not been observed.

### 4.3 Single‑Instance Deployment (Pre‑GAP‑20)

**What:** In the pilot deployment, UICP runs as a single Docker container. If the container or host fails, enforcement stops until the operator follows the recovery procedures.

**Status:** Accepted for pilot. GAP‑20 (Redundancy) will add multi‑instance deployment with load balancing and automatic failover. Until then, the 4‑hour RTO defined in the Business Continuity Plan applies.

---

## 5. FUTURE ADVERSARIAL TESTING

UICP commits to ongoing adversarial evaluation:

- **Annual external review:** An independent evaluator will be engaged to test UICP against its documented claims.
- **Bug bounty program:** A responsible disclosure policy and bounty program will be established before production deployment, with rewards of $500–$5,000 per qualified vulnerability.
- **Continuous fuzz testing:** The fuzz harness will be expanded to cover additional constraint types and binding patterns as new features are added.
- **Public verification:** The public wrappers and verification scripts in the GitHub repository enable any external party to independently verify UICP's determinism and correctness claims without access to the internal engines.

---

## 6. CONCLUSION

UICP was designed for adversarial scrutiny from the start. It has been tested by external evaluators, fuzz‑tested across thousands of constraint combinations, and hardened against the specific attacks identified during evaluation. The design decisions documented in this file — pipeline ordering, fail‑safe defaults, cryptographic audit integrity, Ed25519 non‑repudiation — are direct responses to real or hypothetical attacks.

This document is evidence that UICP was not built in a vacuum. It was challenged, broken, fixed, and re‑validated. The adversarial testing process is ongoing, and new findings will be added to this document as they are discovered and remediated.

---

**END OF ADVERSARIAL DESIGN RATIONALE**
