# UICP System Bible — Part 1: System Overview

**Version 1.0 — June 2026**
**Audience:** Everyone. This is the first document anyone reads about UICP.

If you read nothing else, read this. It tells you what UICP is, why it
exists, how it works, and what evidence proves it works. No technical
background is required for Sections 1‑4. Sections 5‑7 assume basic
familiarity with software systems.

---

## 1. WHAT UICP IS

UICP is a **deterministic constraint enforcement gateway for artificial
intelligence.**

That sentence deserves to be unpacked because every word is deliberate.

**Deterministic** means that given the same inputs, UICP always produces
the same output. There is no randomness. There are no confidence scores.
There is no "maybe." A rule is either satisfied or violated. The outcome
is binary. This property has been validated with over 230 automated tests
across five engine phases, and it is the foundation of everything UICP
does.

**Constraint enforcement** means that UICP checks outputs against formal
rules. A constraint is a simple mathematical statement: "age ≥ 18," or
"risk_score ≤ 20," or "refund_amount ≤ tax_paid." These constraints are
written by a human operator — a compliance officer, a clinician, a
procurement specialist — and loaded into UICP before any decisions are
made. UICP does not invent constraints. It enforces whatever constraints
it is given.

**Gateway** means that UICP sits between an AI model and the real world.
The model produces an output. Before that output reaches a customer, a
patient, a regulator, or a payment system, it passes through UICP. If the
output satisfies all registered constraints, UICP allows it through. If
it violates any constraint, UICP blocks it. If critical data is missing
and a constraint cannot be checked, UICP blocks it. There is no silent
failure. There is no default allow.

**For artificial intelligence** means that UICP is designed to work with
AI models — large language models, machine learning systems, automated
decision engines, or any software that produces outputs that must obey
rules. UICP does not care which model produced the output. It does not
care which company built the model. It only cares about the rules it has
been given and the output it receives.

In one sentence: **UICP proves that AI outputs obey rules.**

---

## 2. THE PROBLEM UICP SOLVES

Every organisation that uses AI has rules. A bank must not approve loans
for applicants under 18. A hospital must not prescribe penicillin to
patients with a documented allergy. A tax authority must not issue refunds
that exceed tax paid. A peacekeeping mission must not engage targets
within 50 metres of a school.

These rules exist in policy documents, in clinical guidelines, in
legislation, in cabinet minutes. They do not exist in the code that checks
the AI model's output.

Today, organisations rely on four approaches to enforce these rules. All
four have the same fatal flaw: they cannot produce proof that a specific
rule was checked on a specific output.

**Prompt engineering** asks the model to follow rules by including them in
the instructions. The model may comply most of the time. When it does not,
there is no enforcement mechanism. The violation is discovered later —
in an audit, in a lawsuit, or in a fatality report.

**Constitutional AI** trains the model to internalise principles during
fine‑tuning. The alignment is statistical, not deterministic. A model
trained on a constitution can still violate it. And there is no per‑output
proof that a specific principle was followed.

**Safety classifiers** use a separate model to flag harmful outputs. They
return confidence scores, not deterministic verdicts. They can be bypassed
by adversarial inputs. They produce no cryptographic proof. They live
inside the AI vendor's ecosystem — an external auditor cannot verify them
independently.

**Human review** requires a person to check every output manually. Humans
miss violations — especially at scale, when hundreds or thousands of
outputs must be reviewed daily. Human review is expensive, inconsistent,
and produces no immutable audit record.

The gap is the same in every case: the rule exists, the enforcement does
not, and there is no proof either way.

UICP closes that gap.

---

## 3. HOW UICP WORKS

UICP is a pipeline with five stages. Understanding what each stage does
is important. Understanding that each stage has been independently
validated with automated tests is more important. The five stages are
described below at the level of detail that matters for understanding.
The internal algorithms that implement each stage are part of the UICP
enforcement engines and are protected by controlled disclosure.

### Stage 1 — Structural Normalisation

Raw constraints arrive as human‑written text: "x > 5," or "5 < x," or
"x > (2 + 3)." These are different ways of expressing the same rule.
Stage 1 normalises them into a single, canonical form. Every
syntactically equivalent constraint collapses to an identical canonical
identity string. This guarantees that two operators writing the same
rule in different ways will produce the same constraint. The output of
Stage 1 is a deterministic, bounded, sorted canonical representation.

**Validated:** 26/26 tests pass. 10,368 fuzz test cases with zero
collision bugs.

### Stage 2 — Single‑Variable Semantic Analysis

Constraints involving a single variable — "age ≥ 18," "risk ≤ 20" — are
analysed for equivalence, dominance, and conflict. If two constraints are
semantically equivalent (e.g., x > 5 and x ≥ 6 over integers), they are
grouped. If one constraint strictly implies another (e.g., x > 10 implies
x > 5), the weaker is removed. If two constraints contradict each other
(e.g., x > 10 and x < 5), the conflict is detected and the constraint set
is rejected. Constraints involving multiple variables are enriched with
algebraic coefficients for Stage 3.

**Validated:** 14/14 tests pass.

### Stage 3 — Multi‑Variable Canonicalisation

Constraints involving multiple variables — "x + y > 10," "2x ‑ y ≤ 5" —
are reduced to a minimal, unique canonical form. Redundant constraints
are eliminated. Unsatisfiable systems are detected and rejected.
Nonlinear constraints (e.g., multiplication of two variables) are detected
and classified. The output is the minimal set of constraints that is
semantically equivalent to the input — the same input always produces the
identical canonical set.

**Validated:** 21/21 tests pass. 11/11 integration tests pass.

### Stage 4 — Enforcement Gateway

This is the runtime stage. A model output arrives as text. The binding
extraction layer — a configurable module that uses regex, JSONPath, tag
delimiters, or constant injection — extracts numeric bindings from the
text (e.g., "age: 35" becomes {"age": 35}). Every constraint from the
canonical set is evaluated against these bindings using pure integer
arithmetic. All violations are collected. The decision is ALLOW if zero
constraints are violated, BLOCK otherwise.

The gateway also enforces fail‑safe semantics. If the bindings are missing
a required variable, the gateway returns BLOCK with a MISSING_VARIABLE
reason. If the gateway itself encounters an internal error, it returns
GATEWAY_UNAVAILABLE — never ALLOW. There is no silent failure path.

Every decision is cryptographically signed with Ed25519 and appended to
an immutable, append‑only audit chain secured by SHA‑256 hashes.

**Validated:** 73/73 tests pass.

### Stage 5 — Trust and Audit

This is the governance layer. Constraint sets are cryptographically
committed by authorised operators using Ed25519 signatures. Production
deployments require two independent operator signatures before a
constraint set becomes active — a control on the governance process
itself.

Every enforcement decision is paired with a verifiable compliance proof.
The proof contains the commitment ID, the decision ID, the status, and a
gateway signature. Any third party — a regulator, an auditor, a grant
committee — can verify the proof using only public keys and the exported
audit bundle. No access to the enforcement engine is required.

The audit log is a complete, append‑only, cryptographically chained
record of every decision. It supports external anchoring for cross‑session
verification, key rotation and revocation, and GDPR‑compliant erasure
through an off‑chain personal data store with AES‑256‑GCM encryption.

**Validated:** 101/101 tests pass.

---

## 4. THE EVIDENCE

UICP is not a prototype. It is not a proof of concept. It is a validated,
tested, adversarially reviewed system ready for pilot deployment.

**Automated test suite:** 235+ tests pass across five engine phases, plus
17 tests for binding extraction, 35 for the personal data store, 32 for
the REST API, 15 for version control, 20 for canary deployment, 21 for
simulation, 36 for consistency checking, 34 for alert management, and
more. Every test is reproducible. Every test result is in the public
repository.

**External adversarial review:** Two independent evaluators reviewed
Phase 1. One found a real defect — a missing node‑count enforcement in the
admission gate — which was patched, re‑validated, and documented. One
challenged the determinism claim on theoretical grounds and withdrew the
challenge after technical review confirmed that the determinism guarantee
applies to the public interface, which handles all exceptions
deterministically.

**Fuzz testing:** Phase 1 canonicalization was tested with 10,368 randomly
generated constraint combinations. Zero collision bugs were found — no two
semantically distinct constraints produced the same canonical identity.

**Live demonstration:** A narrated 8‑minute video shows UICP enforcing
constraints against a live Llama 3.1 model. Five test cases: ALLOW,
BLOCK (age violation), BLOCK (risk violation), BLOCK (dual violation),
BLOCK (missing variable). The audit bundle is verified at the end.
[Watch on YouTube](https://youtu.be/sGQq4Q-gN6Q)

**Independent verification:** The standalone `verify_uicp_bundle.py`
script validates every cryptographic guarantee — Ed25519 signatures,
SHA‑256 chain integrity, and manifest export IDs — without any access
to the UICP enforcement engines. Any third party can run it.

---

## 5. HOW UICP IS DEPLOYED

UICP is deployed as a **Docker container** running a Flask REST API. The
container exposes two endpoints:

- `POST /enforce` — accepts model output (raw text or pre‑extracted
  bindings) plus a constraint set, and returns an ALLOW/BLOCK decision.
- `GET /health` — returns the gateway status for monitoring.

The container is self‑contained. It requires no external database, no
message queue, no distributed file system. It can run on a free‑tier
cloud VM, an on‑premises server, or a developer's laptop.

Authentication is via API key in the `X‑API‑Key` header. All requests are
logged to stdout in structured JSON format. The container includes a
Docker health check for orchestration platforms.

The constraint set is loaded from a JSON file at startup. Updating
constraints requires restarting the container with a new file — a
sub‑second operation in a containerised environment. For zero‑downtime
constraint rotation, a ConstraintStore abstraction supports hot reload
from a database or external API.

The binding extraction layer is configured via a JSON schema that maps
variable names to extraction methods (regex, JSONPath, tag, or constant
injection). The schema is signed and version‑controlled.

---

## 6. WHAT UICP DOES NOT DO

Being clear about limitations is as important as being clear about
capabilities. UICP does not:

- **Make decisions.** UICP enforces constraints. The human operator makes
  the final decision. UICP says ALLOW or BLOCK. The operator decides what
  to do with that information.
- **Learn from data.** UICP is not a machine learning system. It does not
  train on examples. It does not improve over time. It is formal logic
  with cryptographic proofs.
- **Detect bias or discrimination.** UICP enforces whatever constraints it
  is given. If the constraints are biased, UICP will enforce biased
  constraints correctly. The ethical weight of the constraints belongs to
  the constraint‑definer, not to UICP.
- **Verify the accuracy of extracted bindings.** If the extraction schema
  misreads a model output, UICP will enforce constraints on the wrong
  values. Extraction accuracy is the operator's responsibility.
- **Replace existing safety tools.** UICP complements prompt engineering,
  fine‑tuning, guardrails, and human review. It adds the one thing none
  of them provide: deterministic, auditable proof of enforcement.

---

## 7. THE PATH TO ADOPTION

UICP is offered under a three‑tier model:

- **Pilot (free):** 30 days, up to 1,000 decisions/month, one constraint
  set. For organisations evaluating UICP.
- **Standard ($500/month):** Up to 100,000 decisions/month, 5 constraint
  sets, multi‑tenant support, email support, 99.5% SLA.
- **Enterprise ($2,000/month):** Unlimited decisions, unlimited
  constraints, unlimited tenants, SOC 2 Type II certification, dedicated
  support engineer, 99.9% SLA, 24/7.

The pilot requires no financial commitment. If UICP does not deliver
measurable protection against rule violations, the pilot partner walks
away with no obligation.

The onboarding checklist, pilot agreement template, data processing
agreement, and master service agreement are all available in the public
repository. A partner can go from first contact to live enforcement in
under four hours of technical work.

---

## 8. WHAT TO READ NEXT

- **Part 2 — Architecture:** The technical design of all five phases, the
  REST API, the audit chain, and the cryptographic primitives. For
  engineers and technical evaluators.
- **Part 3 — Verticals:** How UICP applies to 14 sectors — lending,
  healthcare, insurance, tax, procurement, peacekeeping, climate finance,
  and more. Each with real constraints and real scenarios.
- **Part 4 — Operations:** Daily operations, monitoring, incident
  response, key management, constraint updates, and disaster recovery.
- **Part 5 — Governance:** NIST AI RMF alignment, GDPR compliance, SOC 2
  Type II audit plan, EU AI Act mapping, and regulatory content
  governance.
- **Part 6 — Business:** Pricing, contracts, intellectual property,
  engine protection doctrine, and client offboarding.
- **Part 7 — Roles:** Every job role required to operate UICP at scale,
  with skills, salary bands, and hiring triggers.
- **Part 8 — Client‑Facing Resources:** The onboarding checklist, the API
  reference, the knowledge base, and the client intake form.
- **Part 9 — Appendices:** Complete traceability — every GAP closed,
  every test result, every validation run, every adversarial evaluation.

---

## 9. THE CLOSING LINE

UICP was built to answer one question.

Not "Can we make AI safer?" — that question is too broad.

Not "Can we build a better guardrail?" — that question is too narrow.

The question UICP answers is: **"Can we prove that a specific rule was
checked on a specific output at a specific moment in time — and can any
third party verify that proof without trusting us?"**

The answer is yes.

That proof is in the repository. That proof is in the verifier. That proof
is in the live demo.

**We don't ask the model to behave. We prove that it did.**
