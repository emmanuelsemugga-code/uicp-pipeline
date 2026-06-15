# UICP — Global Partnership Guide

**For international organisations, multilateral institutions, and
government agencies that cannot afford a single enforcement failure.**

---

## The Death That Should Never Have Occurred

Every year, according to the World Health Organization, over 134 million
adverse events occur in hospitals across low‑ and middle‑income countries.
2.6 million of those events are fatal.

Some of those deaths happen because a clinician makes an impossible
judgment call under pressure. But many of them happen because a simple
rule was not checked.

A patient has a documented penicillin allergy. It is in their file. An
AI‑assisted prescribing system recommends amoxicillin — a penicillin‑
derivative. The system has no constraint enforcement. It does not check
the patient's allergy record against the medication it is recommending.
The recommendation reaches a junior doctor at the end of a 14‑hour
shift. The doctor does not catch it. The medication is administered.
The patient dies.

The rule existed. "Do not prescribe penicillin‑derivatives to patients
with documented penicillin allergy."

The enforcement did not.

If UICP had been deployed, the constraint would have been checked
deterministically before the recommendation ever reached the doctor.
The recommendation would have been blocked. The violation would have
been logged with cryptographic proof.

The patient would have lived.

This is not a hypothetical. The WHO Patient Safety Flagship reports that
medication errors are the single most common preventable cause of patient
harm globally. The solution is not better AI models. It is deterministic
enforcement of the rules that already exist.

---

## The Pattern That Repeats Across Every Sector

It is not just healthcare.

**At the United Nations,** peacekeeping missions operate under strict
Rules of Engagement. An autonomous surveillance system identifies a
target and recommends engagement. If the target is within 50 metres of
a school, the ROE says "do not engage." But the AI system has no
deterministic enforcement of that rule. The recommendation reaches a
commander. The decision is made in seconds. The aftermath reveals a
violation. The evidence of what was checked — and what was not — is
absent.

**At the World Bank,** billions of dollars in development loans are
disbursed through automated systems. A loan disbursement is recommended
for a project in a region that has not met its governance milestones.
The rule says "disbursement conditional on governance score above
threshold." The AI system recommends approval. The rule was in the
policy document. It was not in the enforcement code. The money is
disbursed. The audit finding comes two years later.

**At tax authorities worldwide,** AI systems recommend refunds, flag
audit targets, and approve payment plans. The IRS alone lost $88 million
to improper Earned Income Tax Credit claims in a single year because
an AI system lacked constraint enforcement. The rule "refund ≤ tax_paid"
was not checked deterministically.

In every case, across every institution, the pattern is the same:
the rule exists. The enforcement does not. The harm is discovered
after the fact — in an audit, in a lawsuit, in a headline.

---

## What UICP Is

UICP is a **deterministic constraint enforcement gateway** for AI.

It sits between an AI model (or any automated decision system) and the
real world. It checks every output against formal rules. If a rule is
violated, the output is blocked — with a signed, immutable record of
what was checked and why it was blocked.

- **Deterministic.** Same input always produces same output. No
  probabilities. No confidence scores. No "maybe."
- **Auditable.** Every decision is signed with Ed25519 and stored in an
  append‑only cryptographic chain. An auditor can verify what happened
  without trusting anyone.
- **External to the system.** UICP does not modify your existing AI,
  database, or workflow. It sits after the model, before the decision
  is executed.
- **Fail‑safe.** If critical data is missing — the allergy record, the
  ROE constraint, the governance score — the output is blocked, not
  silently allowed through.
- **Model‑agnostic.** UICP works with any AI model that produces text
  output. OpenAI. Anthropic. Google. Meta. Llama. Your own custom
  model. It does not matter. UICP only cares about the rules you give it.

UICP does not make decisions. Your officers, clinicians, commanders,
and compliance teams make decisions. UICP proves that the rules were
checked — every time, for every output, with proof that cannot be
fabricated.

---

## How This Helps Your Institution Right Now

**If you are WHO or a national health authority:**
Every AI‑assisted clinical recommendation is checked against patient
allergies, contraindications, and treatment guidelines before it reaches
a clinician. Adverse drug events are blocked before they happen. The
audit trail proves to regulators and insurers that clinical safety
rules were enforced.

**If you are the UN Department of Peace Operations:**
Every autonomous surveillance recommendation is checked against the
mission's Rules of Engagement before a commander sees it. The ROE
constraints are enforced deterministically. The audit trail provides
cryptographic evidence for after‑action review and international
tribunals.

**If you are the World Bank or a regional development bank:**
Every loan disbursement, every grant payment, every procurement approval
is checked against governance conditionalities before funds are released.
The proof that conditions were verified is in the audit log — signed,
timestamped, and immutable.

**If you are a national tax authority:**
Every AI‑recommended refund is checked against constraints like
"refund ≤ tax_paid," "taxpayer identity verified," and "no outstanding
audit flags." Improper payments are blocked before they leave the
treasury.

---

## What We Propose — A 30‑Day Free Pilot

We will deploy UICP alongside your existing system for 30 days. No
changes to your current workflow. No downtime. No integration risk.
No financial commitment.

**We provide:**
- The UICP enforcement gateway, deployed on your infrastructure or ours.
- One constraint set (up to 10 rules) defined by your compliance,
  clinical, or legal team.
- Weekly audit bundles with cryptographic verification.
- Technical support throughout the pilot.

**You provide:**
- A designated technical contact.
- Sample (anonymised) data for constraint testing.
- A 30‑minute briefing with your compliance, clinical, or operational
  leadership.

**The pilot costs nothing.** If UICP does not deliver measurable
protection against rule violations, you walk away with no obligation
and a free audit of your current enforcement posture.

---

## The Evidence

We do not ask you to trust us. We ask you to verify.

- **235+ automated tests** passing across five validated engine phases.
- **54 of 55 pre‑deployment gaps closed** — only third‑party audit
  certification deferred until after pilot.
- **Two independent external adversarial evaluations** — one real defect
  found and patched, one challenge withdrawn.
- **10,368 fuzz test cases** with zero collision bugs (Phase 1).
- **Live demo** of enforcement against a real AI model:
  [Watch on YouTube](https://youtu.be/sGQq4Q-gN6Q)
- **Standalone verifier:** Anyone can verify the audit bundle without
  accessing our engine. Run one command:
  ```bash
  python3 verify_uicp_bundle.py audit_export/ public_keys.json
                     Who We Are

UICP was built by Emmanuel Semugga, a Ugandan engineer, tested against
adversarial evaluation by independent reviewers, and validated with
over 230 automated tests. It is the first system of its kind globally
that combines deterministic enforcement, cryptographic proof, and
independent verifiability in a single deployment.

We are not a multinational. We are not a vendor locking you into a
proprietary ecosystem. We are an infrastructure provider. The verification tools are open‑source. The evidence is public. The pilot is free.

---

The Only Question That Matters

Your institution already has rules. They exist in policy documents, in
clinical guidelines, in ROE cards, in loan conditionalities, in tax codes.

What you do not have is proof that those rules are enforced — every
time, for every decision, with a record that cannot be altered or
deleted.

UICP provides that proof.
                     The pilot is free. The evidence is public. The verifier is open‑source.

What do you have to lose?

---

Contact: Emmanuel Semugga — emmanuelsemugga@gmail.com
Repository: github.com/emmanuelsemugga-code/uicp-pipeline
YouTube Demo: https://youtu.be/sGQq4Q-gN6Q
