# UICP Onboarding Checklist

**For pilot partners integrating UICP into their AI decision pipeline.**

This checklist covers the five stages of onboarding: preparation,
deployment, constraint definition, testing, and going live. Each stage
must be completed before the next begins. Estimated total time for a
technical team: 2‑4 hours.

---

## Stage 1 — Preparation (Before Deployment)

- [ ] Confirm access to the UICP REST API endpoint (provided by UICP team).
- [ ] Confirm API key is received and stored securely.
- [ ] Identify the AI model whose outputs will be enforced.
  - Model name and version:
  - Typical output format (plain text, JSON, or structured text):
- [ ] List the constraints that must be enforced on model outputs.
  - Example: `age >= 18`, `risk_score <= 25`, `income >= 50000`.
- [ ] Identify the variables that must be extracted from each model output.
  - Example: `age`, `risk_score`, `income`.
- [ ] Confirm that the model's output format is consistent enough for
  regex‑based or JSONPath‑based extraction.
- [ ] Assign an internal owner for UICP integration (name and email):
- [ ] Schedule a 30‑minute kickoff call with the UICP team.

---

## Stage 2 — Deployment

- [ ] Deploy the UICP Docker container on your infrastructure, or confirm
  access to the managed UICP endpoint.
- [ ] Verify the health check endpoint:
  ```bash
  curl https://your-uicp-endpoint/health
  Expected response: {"status":"healthy"}

· Confirm the API key works:
  ```bash
  curl -X POST https://your-uicp-endpoint/enforce \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your-api-key" \
    -d '{"bindings":{"test":1},"constraint_set":{"constraints":["test >= 0"]}}'
  ```
  Expected response: {"status":"ALLOW",...}
· Verify that the constraint set file is correctly loaded and
  accessible.
  Stage 3 — Constraint Definition

· Write each constraint in canonical form (e.g., age >= 18).
· Create the extraction schema for your model's output format.
  · For each variable, specify the extraction method: regex, JSONPath,
    tag, or constant.
  · Example:
    ```json
    {
      "age": {"method": "regex", "pattern": "age[=: ]*(?P<value>\\d+)"},
      "risk_score": {"method": "regex", "pattern": "risk[=: ]*(?P<value>\\d+)"}
    }
    ```
    Test the extraction schema against sample model outputs using the
  UICP test endpoint.
· Register the constraint set and extraction schema with the UICP
  team for validation.
· Run the Constraint Validator (GAP‑32) to detect syntax errors,
  contradictions, and missing variables before deployment.
· Run the Simulation Engine (GAP‑33) against historical decisions to
  preview the impact of the new constraints.

---

Stage 4 — Testing
Send 10‑20 sample model outputs through the /enforce endpoint and
  verify each decision manually.
  · Test a compliant case (expected: ALLOW).
  · Test a violation case (expected: BLOCK).
  · Test a missing‑variable case (expected: BLOCK with MISSING_VARIABLE
    reason).
· Confirm that BLOCK decisions include violation details with the
  correct constraint identity and expected value.
· Verify that ALLOW decisions return an empty violations list.
· Verify that the audit bundle can be downloaded and verified:
  ```bash
python3 verify_uicp_bundle.py audit_export/ public_keys.json
  ```
  Expected output: all checks PASS.
· Test the extraction schema against 50+ real model outputs to
  confirm extraction accuracy.

---

Stage 5 — Going Live

· Confirm that the UICP endpoint is integrated into your production
  decision pipeline (after the model, before the decision is executed).
· Set up monitoring for the UICP endpoint (health check every 60
  seconds).
· Configure alerts for:
Gateway unavailable (status GATEWAY_UNAVAILABLE).
  · Sudden increase in BLOCK rate (may indicate constraint or extraction
    issue).
  · Audit log export failures.
· Schedule weekly audit bundle exports and verification.
· Assign an internal responder for UICP alerts (name and email):
· Schedule a 30‑day check‑in with the UICP team to review performance.

---

Support during onboarding:

· Email: emmanuelsemugga@gmail.com
· Response time: within 1 business day for pilot partners.
Emergency: contact the UICP team directly by phone for
  gateway‑unavailable incidents.

After onboarding is complete, the pilot agreement governs ongoing
support, data handling, and service levels.
