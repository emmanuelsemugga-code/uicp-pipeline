# UICP Engine Protection Doctrine

**Why the enforcement engines are not open‑source, and why that is the
correct decision for AI governance infrastructure.**

---

## The Short Answer

The UICP enforcement engines are the only implementation of deterministic
constraint enforcement with cryptographic proof that has been validated by
external adversarial review. They are protected by controlled disclosure —
the same model used by every major infrastructure company — to prevent
unauthorised replication while enabling full independent verification.

You can verify every claim UICP makes without ever seeing the engine source
code. The public repository contains everything required for independent
verification: public wrappers, verification scripts, external adversarial
validation documents, and a standalone audit bundle verifier.

---

## What Is In The Public Repository

The public repository at `github.com/emmanuelsemugga-code/uicp-pipeline`
contains:

- **Public wrappers** for all five pipeline phases (normalize.py,
  phase2_public.py, phase3_public.py, phase4_public.py, phase5_public.py).
  These are thin interfaces that expose the validated output contracts
  without revealing internal algorithms.
- **Adversarial verification scripts** (verify_phase1_claims.py through
  verify_phase5_claims.py) that reproduce every claim test and can be run
  by any party with access to the internal engines.
- **Master verification script** (verify_all_phases.py) that runs all five
  phases in sequence.
- **Standalone audit bundle verifier** (verify_uicp_bundle.py) that
  verifies Ed25519 decision signatures, SHA‑256 chain integrity, and
  manifest export IDs — without any access to the internal engines.
- **External adversarial validation documents** for all five phases,
  describing every claim, test vectors, and challenge instructions.
- **REST API layer** (app/api.py, app/auth.py, app/logging.py,
  app/errors.py) — the complete Flask application that exposes UICP over
  HTTP. This code is public and auditable.
- **Tier 2 durability modules** — validation framework, version control,
  dependency analysis, canary deployment, simulation engine, consistency
  checker, alert manager, audit archiver, performance profiler, and more.
  All are public.
- **Complete documentation** — architecture specification, security model,
  regulatory mapping, operator manual, legal assessment, GDPR privacy
  impact assessment, business continuity plan, incident response procedure,
  NIST alignment documents, and governance protocols.

---

## What Is NOT In The Public Repository

The following files are excluded via `.gitignore` and are never pushed to
the public repository:

- `normalize_v05.py` — Phase 1 structural normalization engine
- `phase2_engine.py` — Phase 2 single‑variable semantic analysis engine
- `phase3_engine.py` — Phase 3 multi‑variable canonicalization engine
- `phase4_engine.py` — Phase 4 enforcement gateway engine
- `phase5_engine.py` — Phase 5 trust and audit engine
- `engines/` — the entire engines directory

These files contain the proprietary enforcement logic — the pipeline order,
admission gate, normalization algorithms, semantic analysis rules,
cryptographic signing logic, and audit chain construction. They are the
result of rigorous adversarial testing and represent the core intellectual
property of UICP.

---

## Why Controlled Disclosure?

### 1. Trade‑Secret Protection

The UICP enforcement pipeline is the result of a specific sequence of
transformations — constant folding, algebraic simplification, relational
normalization, boolean flattening, boolean simplification, and operand
sorting — developed through iterative adversarial testing. This pipeline
order is proprietary. Making it public would enable competitors to
replicate the enforcement logic without investing in the adversarial
validation process.

### 2. Infrastructure Precedent

Every major infrastructure company protects its core engines:

- Google does not open‑source its search ranking algorithm.
- Cloudflare does not open‑source its DDoS mitigation engine.
- AWS does not open‑source its hypervisor.

These companies provide public verification mechanisms (status pages,
audit reports, API documentation) without exposing their internal
implementations. UICP follows the same model: the public repository proves
the system works; the engines are available under controlled disclosure for
clients and their designated auditors.

### 3. Independent Verification Without Engine Access

The `verify_uicp_bundle.py` script proves that full cryptographic
verification is possible without engine access. The script:

- Requires only Python 3.12 and the `cryptography` library — both free and
  open‑source.
- Contains zero UICP source code.
- Verifies Ed25519 decision signatures, SHA‑256 chain hashes, manifest
  integrity, and proof signatures.
- Can be run by any regulator, auditor, grant committee, or third party.

This means the enforcement engine's correctness can be verified at the
output level — by checking the cryptographic proofs — without inspecting
the internal logic. This is the same model used by certificate authorities,
hardware security modules, and financial audit systems.

---

## Who Gets Access To The Engines?

Access to the internal engines is granted under the following conditions:

- **Paying clients** (Tiers 2‑3) receive access for internal deployment and
  integration.
- **External auditors** retained by clients receive access under NDA for
  the purpose of validating the client's deployment.
- **Regulatory bodies** with statutory authority receive access upon
  written request and executed protective order.
- **Grant committees and funding agencies** may request access for the
  purpose of technical due diligence.

Access is never granted to competitors, to the general public, or to any
party that refuses to sign a non‑disclosure agreement.

---

## What Happens If The Engines Leak?

If the engine source code is published without authorisation:

1. The trade‑secret status is preserved by the controlled disclosure model.
   Publication without authorisation constitutes trade‑secret
   misappropriation and is actionable under the Defend Trade Secrets Act
   (United States) and equivalent legislation in other jurisdictions.
2. The public verification mechanism remains intact. The engines can be
   re‑implemented by a competitor, but the validation baseline — 235+
   automated tests, external adversarial reviews, and cryptographic proof
   — cannot be faked. A re‑implementation that passes the same verification
   suite would take months of adversarial testing.
3. New engine versions would be released with updated validation baselines,
   making any leaked version obsolete within one release cycle.

The system is designed so that the engines are valuable but not
irreplaceable. The value is in the validation, the adversarial testing, and
the trust that has been built — not in the code alone.

---

## How To Request Access

To request access to the internal engines for evaluation, auditing, or
deployment, contact:

**Emmanuel Semugga**
**emmanuelsemugga@gmail.com**

Please include:
- Your name and organisation
- The purpose of the access request (deployment, audit, regulatory review)
- Whether you are willing to sign a non‑disclosure agreement

Access decisions are made within 5 business days.

---

**"We don't ask the model to behave. We prove that it did."**
