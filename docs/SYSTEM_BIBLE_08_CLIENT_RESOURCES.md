```markdown
# UICP System Bible — Part 8: Client‑Facing Resources

**Version 1.0 — June 2026**
**Audience:** New and existing clients integrating UICP into their AI
decision pipeline.

---

This document is the single entry point for every resource a client
needs. It assumes you have just heard about UICP and want to
understand what it does, whether it fits your use case, and how to
get it running in your environment. Every resource referenced here
is available in the public repository at:

**github.com/emmanuelsemugga-code/uicp-pipeline**

---

## 1. START HERE — THE ONE‑PAGER

If you read nothing else, read the one‑pager. It tells you what
UICP is, what problem it solves, who needs it, and how to verify it
independently. It takes less than five minutes.

**Document:** `docs/ONE_PAGER.md`

After reading the one‑pager, you should know:
- Whether UICP is relevant to your organisation.
- What evidence exists that UICP works.
- How to verify the cryptographic claims yourself.

---

## 2. SEE UICP IN ACTION

A narrated 8‑minute video shows UICP enforcing constraints against a
live Llama 3.1 model. Five test cases: ALLOW, BLOCK (age violation),
BLOCK (risk violation), BLOCK (dual violation), BLOCK (missing
variable). The audit bundle is verified at the end.

**Watch the demo:** [YouTube](https://youtu.be/sGQq4Q-gN6Q)

---

## 3. UNDERSTAND HOW UICP WORKS

The System Bible is the complete reference for UICP. The most
important parts for a new client are:

- **Part 1 — System Overview:** What UICP is, the problem it solves,
  the evidence that it works. Start here if you are evaluating UICP
  for the first time.
- **Part 2 — Architecture:** The technical design of all five phases,
  the REST API, the audit chain, and the cryptographic primitives.
  Read this if you are an engineer integrating UICP.
- **Part 3 — Verticals:** How UICP applies to 14 sectors. Find your
  industry and see example constraints. Read this if you want to
  understand how UICP fits your specific use case.
- **Part 4 — Operations:** Daily operations, monitoring, incident
  response, key management. Read this if you are responsible for
  keeping UICP running.

**Documents:** `docs/SYSTEM_BIBLE_01_OVERVIEW.md` through
`docs/SYSTEM_BIBLE_09_APPENDICES.md`

---

## 4. INTEGRATE UICP — THE ONBOARDING CHECKLIST

The onboarding checklist walks you through every stage of
integration, from confirming API access to going live in production.
Each stage has a checkbox you can tick off. Estimated total time
for a technical team: 2‑4 hours.

**Stages covered:**
1. Preparation (API key, model identification, constraint list).
2. Deployment (Docker container, health check, API key verification).
3. Constraint definition (canonical forms, extraction schema,
   validation, simulation).
4. Testing (sample outputs, BLOCK/ALLOW verification, audit bundle
   verification).
5. Going live (monitoring, alerts, weekly audit bundle exports).

**Document:** `docs/ONBOARDING_CHECKLIST.md`

---

## 5. THE REST API REFERENCE

UICP is accessed via a Flask REST API with two endpoints:

### `GET /health`
Returns `{"status":"healthy"}` and HTTP 200. Used for Docker
health checks and monitoring.

### `POST /enforce`
Accepts model outputs and constraint sets, returns ALLOW/BLOCK
decisions with violation details.

**Two request modes:**

**Mode 1 — Raw model output:**
```json
{
  "model_output": "Loan for client age: 35. Risk score: 8. APPROVE.",
  "binding_schema": {
    "age": {"method": "regex", "pattern": "age[=: ]*(?P<value>\\d+)"},
    "risk": {"method": "regex", "pattern": "risk[=: ]*(?P<value>\\d+)"}
  },
  "constraint_set": {
    "objective_id": "LOAN_APPROVAL",
    "constraints": ["age >= 18", "risk <= 20"]
  }
}
```

Mode 2 — Pre‑extracted bindings:

```json
{
  "bindings": {"age": 35, "risk": 8},
  "constraint_set": {
    "objective_id": "LOAN_APPROVAL",
    "constraints": ["age >= 18", "risk <= 20"]
  }
}
```

Response (ALLOW):

```json
{
  "status": "ALLOW",
  "violations": [],
  "decision_id": "abc123...",
  "output_id": "req-001",
  "timestamp": "2026-06-15T12:00:00Z"
}
```

Response (BLOCK):

```json
{
  "status": "BLOCK",
  "violations": [
    {
      "constraint_identity": "C_AGE",
      "canonical_form": "age >= 18",
      "actual_value_hash": "sha256...",
      "expected": "age >= 18"
    }
  ],
  "decision_id": "def456...",
  "output_id": "req-002",
  "timestamp": "2026-06-15T12:01:00Z"
}
```

Authentication: Include X‑API‑Key header with every request.

Error responses: All errors return a standard JSON envelope with
error_type, message, retryable flag, and request_id.

Detailed specification: The OpenAPI specification will be available
at docs/uicp-openapi.yaml in a future release.

---

6. THE KNOWLEDGE BASE

Common questions are answered in the public knowledge base. Before
contacting support, search for your question here.

Frequently Asked Questions

Q: What happens if the UICP gateway goes down?
A: All decisions should be routed to manual review. The gateway
returns GATEWAY_UNAVAILABLE when it cannot safely proceed. Your
system should treat this the same as a BLOCK — do not allow the
decision to proceed without human review.

Q: How do I update constraints without downtime?
A: Edit the constraint set JSON file, restart the Docker container.
Total downtime: less than 2 seconds. For zero‑downtime rotation,
use the ConstraintStore abstraction with hot reload.

Q: Can UICP enforce constraints on outputs from any AI model?
A: Yes. UICP is model‑agnostic. It works with OpenAI, Anthropic,
Google, Meta, Llama, custom models — any model that produces text
output that can be parsed by an extraction schema.

Q: What happens if my extraction schema misreads the model output?
A: UICP enforces constraints on the values it receives. If the
extraction schema extracts age: 35 when the model said age: 16,
UICP will enforce constraints on the wrong value. Extraction accuracy
is your responsibility. Test your schema thoroughly before going live.

Q: How do I verify the audit bundle?
A: Run the standalone verifier:

```bash
python3 verify_uicp_bundle.py audit_export/ public_keys.json
```

Expected output: all checks PASS.

Q: What if I need a constraint that involves division or nonlinear
operations?
A: UICP supports linear integer arithmetic only. Nonlinear constraints
are detected and classified as NONLINEAR. They are preserved in the
constraint set but cannot be automatically enforced. Contact UICP to
discuss whether your constraint can be reformulated.

---

7. THE CLIENT INTAKE FORM

If you are ready to start a pilot, fill out the client intake form.
This helps us prepare your environment before the first call.

What the form asks:

1. Organisation name and contact person.
2. Use case description — what AI model are you using, and what
   decisions does it make?
3. Constraints — list the rules you want enforced (e.g., "age >= 18",
   "risk_score <= 20"). We will help you formalise them.
4. Model output format — provide 3‑5 sample model outputs so we can
   design your extraction schema.
5. Expected decision volume — how many decisions per day or month?
6. Deployment preference — do you want UICP deployed on your
   infrastructure, or do you prefer a managed endpoint?
7. Regulatory requirements — list any specific regulations you must
   comply with (GDPR, NIST, EU AI Act, sectoral rules).

Form location: A Google Form link will be added to the repository
and the README. For now, email the above information to:

emmanuelsemugga@gmail.com

---

8. WHAT TO DO WHEN SOMETHING GOES WRONG

Gateway unavailable: Follow the incident response procedure in the
Operations guide (docs/SYSTEM_BIBLE_04_OPERATIONS.md, Section 3).

Unexpected BLOCK rate: Check extraction schema, constraint changes,
and model updates. Escalate to support if unexplained.

Audit verification fails: Stop processing decisions immediately.
Contact UICP support. Do not delete any log files — they will be
needed for forensic analysis.

Support escalation: docs/SUPPORT_ESCALATION.md

---

9. NEXT IN THE SYSTEM BIBLE

· Part 9 — Appendices: Complete traceability — every GAP closed,
  every test result, every validation run, every adversarial evaluation.

```
