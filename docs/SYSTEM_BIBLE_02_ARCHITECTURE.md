# UICP System Bible — Part 2: Architecture

**Version 1.0 — June 2026**
**Audience:** Engineers, technical evaluators, auditors, and anyone who
needs to understand how UICP works under the hood — without accessing
the internal engine source code.

---

## 1. HIGH‑LEVEL ARCHITECTURE

UICP is a pipeline of five sequential phases, followed by a REST API
layer for runtime enforcement and a trust and audit layer for governance.
┌─────────────────────────────────────────────────────────────────┐
│                        OFFLINE (BUILD TIME)                     │
│                                                                 │
│  Phase 1           Phase 2           Phase 3                    │
│  Structural        Single‑Variable   Multi‑Variable             │
│  Normalization     Semantic          Canonicalization           │
│  (26/26 tests)     Analysis          (21/21 tests)              │
│                    (14/14 tests)                                │
│       ↓                 ↓                 ↓                     │
│  Canonical         Enriched          Minimal                    │
│  Identity          Constraints       Canonical Set              │
│  Strings           with Coefficients                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        ONLINE (RUNTIME)                         │
│                                                                 │
│  Binding           Phase 4           Phase 5                    │
│  Extraction        Enforcement       Trust &                    │
│  Layer             Gateway           Audit Engine               │
│  (84/84 tests)     (73/73 tests)     (101/101 tests)            │
│       ↓                 ↓                 ↓                     │
│  Numeric           ALLOW/BLOCK       Signed Proofs              │
│  Bindings          Decision          Audit Log                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        EXPOSURE LAYER                           │
│                                                                 │
│  Flask REST API     Standalone         Docker                   │
│  /enforce           Verifier           Container                │
│  /health            verify_uicp_       (port 5000)              │
│                     bundle.py                                   │
└─────────────────────────────────────────────────────────────────┘

```
The first three phases run offline — they process constraints into a
canonical form before any model output is ever checked. The remaining
layers run online — they process model outputs at runtime, enforce
constraints, and produce cryptographic proof.

---

## 2. PHASE 1 — STRUCTURAL NORMALIZATION

**Purpose:** Convert raw constraint text into a deterministic canonical
identity string.

**Input:** A set of constraint strings in a constrained DSL (e.g.,
`"x > 5"`, `"age >= 18 AND risk <= 20"`, `"x + y > 10"`).

**Output:** A sorted list of canonical identity strings — JSON‑serialized
canonical ASTs. Each string is a unique, deterministic representation of
the original constraint. The same constraint written in different forms
(`"x > 5"`, `"5 < x"`, `"x > (2+3)"`) all produce the identical
canonical identity.

**What happens inside (high‑level):**

1. **Tokenization** — the constraint string is broken into tokens
   (operators, variables, integers, keywords).
2. **Parsing** — tokens are assembled into an abstract syntax tree.
3. **Constant folding** — all‑constant arithmetic is evaluated at build
   time (`2+3` becomes `5`).
4. **Algebraic simplification** — identity operations are removed
   (`x+0` becomes `x`).
5. **Relational normalization** — operator‑variable order is canonicalized
   (`5 < x` becomes `x > 5`).
6. **Boolean flattening** — nested same‑operator chains are collapsed
   (`A AND (B AND C)` becomes `A AND B AND C`).
7. **Boolean simplification** — idempotent, identity, and absorption
   rules are applied (`A OR (A AND B)` becomes `A`).
8. **Operand sorting** — AND/OR operands are sorted by identity string.

**Guarantees:**
- Deterministic — same input always produces same identity.
- Bounded — no input can cause unbounded structural growth (node count ≤
  256, depth ≤ 32, variables ≤ 64, constraints ≤ 16).
- Idempotent — normalizing the output a second time produces an identical
  result.
- Commutative — AND(A,B) and AND(B,A) produce the same identity.

**Validation:** 26/26 tests pass. 10,368 fuzz test cases with zero
collision bugs. Two independent external adversarial evaluations.

**What Phase 1 does NOT do:**
- It does not evaluate semantic equivalence (`x+1>6` and `x>5` remain
  distinct — that is Phase 2 work).
- It does not reason across constraint boundaries.

---

## 3. PHASE 2 — SINGLE‑VARIABLE SEMANTIC ANALYSIS

**Purpose:** Detect equivalence, dominance, and conflict among
single‑variable constraints. Extract algebraic structure from
multi‑variable constraints for Phase 3.

**Input:** Canonical identity strings from Phase 1.

**Output:** A reduced constraint set with:
- Equivalence groups — constraints that are semantically identical over
  the integer domain (e.g., `x>5` and `x>=6`).
- Dominance removals — constraints that are strictly implied by another
  (e.g., `x>5` is removed if `x>10` is present).
- Conflict detections — constraint pairs that cannot both be satisfied
  (e.g., `x>10` AND `x<5`).
- Multi‑variable extensions — for constraints involving more than one
  variable, the algebraic coefficients are extracted and attached.

**Domain:** Single‑variable linear arithmetic with integer coefficients.

**What Phase 2 does NOT do:**
- Multi‑variable reasoning, canonicalization, or satisfiability (Phase 3).
- Full semantic equivalence for all possible expressions.

**Validation:** 14/14 tests pass.

---

## 4. PHASE 3 — MULTI‑VARIABLE CANONICALIZATION

**Purpose:** Reduce a constraint set to its minimal, unique canonical
form. Detect unsatisfiable systems. Classify nonlinear constraints.

**Input:** The validated output from Phase 2 — including multi‑variable
constraints with extracted coefficients.

**Output:** A minimal canonical constraint set where:
- Every constraint is in a unique canonical form.
- Redundant constraints are eliminated (e.g., `x+y>10` is removed if
  `x>6` and `y>4` are both present, because together they imply `x+y>10`).
- Unsatisfiable systems are detected and reported as CONFLICT.
- Nonlinear constraints are classified as NONLINEAR and preserved
  unchanged.
- Identity ledger is complete — every input identity string appears in
  the output.

**Technique:** Fourier‑Motzkin elimination over exact rational arithmetic
(using Python's `fractions.Fraction` for infinite precision). All
arithmetic is integer‑only — no floating‑point.

**What Phase 3 does NOT do:**
- Solve nonlinear constraints.
- Handle disjunctions (OR) beyond identity preservation.

**Validation:** 21/21 internal tests pass. 11/11 integration tests pass.

---

## 5. BINDING EXTRACTION LAYER

**Purpose:** Convert raw model output text into numeric bindings that the
enforcement gateway can evaluate.

**Location:** Runtime. This is the bridge between an AI model's text
output and the constraint enforcement engine.

**How it works:**
The operator defines a binding schema — a JSON object that maps variable
names to extraction methods. Four methods are supported:

1. **Regex** — applies a regular expression with a named capture group
   `(?P<value>...)` to extract the numeric value.
2. **JSONPath** — uses a dotted path to extract a value from a JSON
   object embedded in the model output.
3. **Tag** — finds delimited values like `[VAR:LOAN_AMOUNT]15000[/VAR]`.
4. **Constant** — injects a fixed value independent of the model output
   (for variables sourced from a trusted database).

The extraction layer also supports:
- **Format hashing** — the exact matched substring is SHA‑256‑hashed to
  create a forensic fingerprint. Different phrasings of the same value
  produce different hashes, enabling prompt‑injection detection.
- **Multi‑match consistency checking** — if a regex matches multiple
  different values in the same output, a warning is flagged.
- **Data minimization** — when a personal data store is available, raw
  values and matched substrings are stored off‑chain. The extraction
  evidence contains only SHA‑256 hash pointers.

**Validation:** 84/84 tests pass (17 original + 20 GAP‑47 Governed Schema
+ 27 GAP‑36 Prompt Injection + 20 GAP‑43 Data Minimization).

---

## 6. PHASE 4 — ENFORCEMENT GATEWAY

**Purpose:** Evaluate constraints against runtime bindings and produce
deterministic ALLOW/BLOCK decisions with cryptographic signatures.

**Location:** Runtime. The gateway receives bindings from the extraction
layer and the canonical constraint set from Phase 3.

**How it works:**

1. **Contract loading** — the canonical constraint set is loaded and
   validated at startup. The gateway becomes immutable after loading.
   Constraints classified as LINEAR_SINGLE_VAR or LINEAR_MULTI_VAR are
   enforceable. NONLINEAR and OUT_OF_SCOPE constraints are logged for
   manual review but do not cause automatic blocks.

2. **Binding validation** — all bindings are validated at runtime:
   - Keys must be strings.
   - Values must be 128‑bit signed integers.
   - Floats, booleans, and strings as values are rejected.
   - Out‑of‑range integers are rejected.
   - Invalid bindings produce an immediate BLOCK.

3. **Constraint evaluation** — every enforceable constraint is evaluated
   against the bindings using pure integer arithmetic. The gateway
   includes a self‑contained recursive‑descent expression parser — no
   `eval()`, no `exec()`, no floating‑point.

4. **Violation collection** — all violated constraints are collected into
   a violations list. Missing variables produce a MISSING_VARIABLE
   violation. Parse errors produce a PARSE_ERROR violation. The gateway
   never short‑circuits — all constraints are always checked.

5. **Decision** — ALLOW if the violations list is empty, BLOCK otherwise.

6. **Fail‑safe semantics** — if the gateway encounters an unexpected
   state (request is not a dict, request is None, internal crash), it
   returns GATEWAY_UNAVAILABLE — a structurally valid BLOCK decision
   with a SYSTEM constraint identity and a diagnostic reason. The gateway
   never raises an unhandled exception. The consuming application always
   receives a decision dict.

7. **Cryptographic signing** — every decision is signed with Ed25519
   using the gateway's private key. The signature covers the decision ID,
   output ID, status, timestamp, and violations. Phase 5 verifies these
   signatures before generating proofs.

8. **Immutable audit chain** — every decision is appended to an
   append‑only log. Each entry is chained to the previous via SHA‑256:
   `chain_hash = SHA256(previous_chain_hash + decision_id)`. The chain is
   cryptographically tamper‑evident.

9. **GDPR compliance** — binding values (which may constitute personal
   data) are extracted from the decision record before computing the
   decision ID. They are replaced with SHA‑256 hash pointers. Raw values
   are stored off‑chain in an encrypted personal data store. Erasure
   deletes the raw value — the hash pointer remains, proving enforcement
   occurred while preserving chain integrity.

**Validation:** 73/73 tests pass (43 original + 15 GAP‑21 fail‑safe + 15
GAP‑42 handoff signing + GAP‑36/GAP‑44 enrichment).

---

## 7. PHASE 5 — TRUST AND AUDIT ENGINE

**Purpose:** Provide cryptographic governance — constraint set
commitments, verifiable compliance proofs, human‑gated overrides, key
lifecycle management, and an externally verifiable audit chain.

**Location:** Runtime. Phase 5 consumes the decision log from Phase 4.

**Three core operations:**

### 7.1 Objective Commitment

Before any enforcement decisions are made, the constraint set is
cryptographically committed. An authorised operator signs a commitment
record with their Ed25519 private key. The commitment binds an objective
ID, a constraint set hash, a version number, and a timestamp. Once
committed, the constraint set cannot be changed without producing a
different commitment hash — making any alteration detectable.

For production deployments, two independent operators must sign the
commitment before it becomes active (two‑person integrity control).

### 7.2 Proof Generation

For every decision in the Phase 4 log, Phase 5 generates a compliance
proof. The proof contains:
- `proof_id` — SHA‑256 of the proof pre‑image.
- `commitment_id` — the objective commitment this proof relates to.
- `decision_id` — the Phase 4 decision ID.
- `status` — ALLOW or BLOCK.
- `proof_signature` — Ed25519 signature by the gateway's private key.

The proof can be verified by any third party with the gateway's public
key, the operator's public key, the commitment, and the decision record.
No access to the enforcement engine is required.

### 7.3 Override Controls

An authorised human operator can override a BLOCK decision using an
Ed25519‑signed override record. The override creates a new log entry —
it never alters the original decision. The model has zero ability to
trigger, request, or influence an override. The operator registry
ensures that only registered operators can sign overrides.

### 7.4 Key Lifecycle Management

All signing keys have defined validity periods (default 12 months).
Keys can be rotated, revoked, or expired:
- **ACTIVE** keys can sign new decisions.
- **ROTATED** keys are replaced; historical signatures remain verifiable.
- **REVOKED** keys are compromised; ALL signatures are rejected.
- **EXPIRED** keys cannot sign; historical signatures remain verifiable.

Key storage requirements are defined for development (in‑memory only),
staging (encrypted file), and production (Hardware Security Module).

### 7.5 Audit Chain

Phase 5 maintains its own append‑only log, cryptographically chained to
the last entry of the Phase 4 chain. The genesis anchor is
`SHA256(phase4_last_chain_hash)`. Every Phase 5 entry — commitment,
proof, or override — is chained via:
`chain_hash = SHA256(previous_hash + record_id)`.

External anchoring (GAP‑12) allows an operator to sign a chain‑state
record, creating a verifiable anchor that can be validated across
sessions. This prevents an attacker from replacing the entire log with a
fabricated chain.

**Validation:** 101/101 tests pass (30 original + 13 GAP‑12 external
anchors + 21 GAP‑11 two‑person signing + 37 GAP‑13/14 key lifecycle).

---

## 8. REST API LAYER

The enforcement gateway is exposed over HTTP via a Flask REST API:

- `POST /enforce` — accepts either raw model output (with extraction
  schema and constraint set) or pre‑extracted bindings (with constraint
  set). Returns the decision dict with HTTP 200 (ALLOW/BLOCK) or 503
  (GATEWAY_UNAVAILABLE).
- `GET /health` — returns `{"status":"healthy"}` for Docker/Kubernetes
  liveness probes.

Authentication is via `X‑API‑Key` header with constant‑time comparison to
prevent timing attacks. All requests are logged to stdout in structured
JSON format (timestamp, masked API key, request ID, endpoint, status code,
latency in milliseconds).

The API layer supports two request modes:
1. **Raw model output mode** — the client sends the model's text output
   plus a binding schema and constraint set. UICP runs extraction and
   enforcement in one call.
2. **Pre‑extracted bindings mode** — the client sends already‑parsed
   numeric bindings plus a constraint set. UICP only enforces.

**Validation:** 32/32 endpoint tests pass.

---

## 9. DOCKER CONTAINER

UICP ships as a single Docker container:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir Flask==3.0.0
COPY engines/ engines/
COPY extraction/ extraction/
COPY export/ export/
COPY tests/ tests/
COPY app/ app/
EXPOSE 5000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health').read()" || exit 1
CMD ["python", "-m", "app.api"]
The container is self‑contained. It requires no external database,
message queue, or distributed file system. It can run on:

· A free‑tier cloud VM (AWS EC2 t3.micro, GCP e2‑micro, Azure B1s).
· An on‑premises Linux server.
· A developer's laptop.

The constraint set is loaded from a file path specified by the
CONSTRAINT_SET_PATH environment variable. The API key is loaded from the
API_KEY environment variable. The personal data store encryption key is
loaded from the PERSONAL_DATA_STORE_KEY environment variable (optional).
10. CRYPTOGRAPHIC PRIMITIVES

UICP uses only standard, widely audited cryptographic primitives:

Primitive Purpose Library
Ed25519 Decision signatures, constraint commitments, proofs, overrides, key lifecycle cryptography
SHA‑256 Decision IDs, proof IDs, commitment IDs, chain hashes, export IDs, format hashes, value hashes hashlib (Python standard)
AES‑256‑GCM Personal data store encryption at rest cryptography
HMAC (SHA‑256) Constant‑time API key comparison hmac (Python standard)
No custom cryptographic code exists in UICP. All cryptographic operations
are delegated to the Python standard library or the cryptography
package — both of which are maintained by the Python Cryptographic
Authority and used in production by thousands of organisations.

---

11. NEXT IN THE SYSTEM BIBLE

· Part 3 — Verticals: How UICP applies to 14 sectors — lending,
  healthcare, insurance, tax, procurement, peacekeeping, climate finance,
  and more. Each with real constraints and real scenarios.
· Part 4 — Operations: Daily operations, monitoring, incident
  response, key management, constraint updates, and disaster recovery.
· Part 5 — Governance: NIST AI RMF alignment, GDPR compliance, SOC 2
  Type II audit plan, EU AI Act mapping.

```
