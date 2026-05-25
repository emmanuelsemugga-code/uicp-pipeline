# UICP Residual Risk Register

## Risk ID: MODEL_OUTPUT_FORGERY_RESIDUAL

**Description:**
Binding values extracted from model outputs may be adversarially
forged while satisfying extraction patterns and signed constraints.
A prompt injection attack can cause the model to emit binding values
that pass all enforcement checks while misrepresenting the actual
decision context.

**Root cause:**
The generative model is a probabilistic, non‑verifiable source.
No code patch can eliminate the possibility of format‑compliant
adversarial outputs from a generative model.

**Technical mitigations implemented (GAP‑36):**
- format_hash: forensic fingerprint of exact extraction substring
- decision_hash: binds decision to extraction evidence
- Multi‑value consistency check: detects injection signals
- TrustedSourceRegistry: verifies values against authoritative source
- binding_evidence: full extraction audit trail per decision

**Residual probability:**
Non‑zero. Empirically measurable via red‑team campaigns on the
target model family. Cannot be reduced to zero by code alone.

**Impact:**
Potential unauthorized ALLOW decisions where injected binding
values satisfy constraints but misrepresent actual applicant data.

**Treatment:**
- Accepted with monitoring
- Human oversight mandatory for high‑stakes decisions
- Periodic red‑team campaigns against deployed model
- Fallback to TrustedSourceRegistry when authoritative data available
- Human‑in‑loop escalation when injection_warnings are present

**Owner:** Security and Architecture team
**Review cadence:** Quarterly
**Last reviewed:** May 2026
**Next review due:** August 2026
