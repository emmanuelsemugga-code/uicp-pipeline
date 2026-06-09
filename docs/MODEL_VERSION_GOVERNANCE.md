# UICP Model Version Governance

## Version 1.0 — Final
### Status: Active
### Audience: CTOs, Compliance Officers, AI Governance Leads, Regulators

---

## 1. PURPOSE

Every AI model in production will be updated. When a financial institution upgrades its credit‑scoring model from v2.3 to v2.4, or a hospital deploys a new diagnostic assistant, or a government agency retrains its benefits‑eligibility predictor — the constraints that govern those models must be reviewed, tested, and re‑validated.

Without a formal governance process, a model update can silently invalidate previously validated constraints. The extraction schema may break. The constraint thresholds may become incorrect. The audit trail may contain decisions made under incompatible constraint versions.

UICP provides the enforcement layer. This document provides the governance process that ensures model updates do not create enforcement gaps. It is designed to satisfy:

- **EU AI Act Article 17** (quality management system)
- **NIST AI RMF Govern 2.0** (organisational governance of AI systems)
- **ISO/IEC 42001 Clause 8.1** (operational planning and control)
- **SOC 2 CC3.1** (change management controls)

This document is not a recommendation. It is the mandatory governance protocol for any organisation deploying UICP with a production AI model.

---

## 2. SCOPE

This governance protocol applies to any change to a model that:

- Alters the model's output format (e.g., new JSON structure, different variable naming).
- Changes the model's behaviour on inputs that are subject to constraints (e.g., a credit‑scoring model that now produces different scores for the same applicant).
- Introduces new variables that should be constrained.
- Removes variables that were previously constrained.
- Is deployed to production and whose outputs will be enforced by UICP.

It does NOT apply to:

- Internal experimentation or research models that do not feed into UICP enforcement.
- Models whose outputs are not subject to any registered constraints.
- Non‑production environments (staging, development) — though testing in those environments is required before production deployment.

---

## 3. GOVERNANCE WORKFLOW

Every model version change follows a five‑stage gated workflow. No stage may be skipped. Each stage produces an auditable record.

### Stage 1 — Impact Assessment

**Who:** Model owner + Constraint owner
**What:** Determine whether the model change affects any registered constraint.

**Required actions:**
1. Identify all constraints currently registered for this model.
2. For each constraint, determine whether the model change could affect:
   - The variable names used in the constraint (e.g., `credit_score` renamed to `fico_score`).
   - The value range produced by the model (e.g., a score that previously ranged 300‑850 now ranges 200‑1000).
   - The presence or absence of a variable (e.g., a new model no longer produces `debt_ratio`).
3. Document the impact assessment in the Model Change Register.

**Output:** Impact Assessment Record, signed by both the model owner and constraint owner.

**Gate:** If the assessment determines that NO constraints are affected, proceed to Stage 4 (Deployment). If any constraint is affected, proceed to Stage 2.

---

### Stage 2 — Constraint Review & Update

**Who:** Constraint owner + Compliance officer
**What:** Review and update all affected constraints.

**Required actions:**
1. For each affected constraint, determine whether the constraint must be:
   - **Unchanged** (the model change does not affect the constraint's logic).
   - **Updated** (the constraint's canonical form must change, e.g., a threshold adjustment).
   - **Added** (a new constraint is needed for a new variable).
   - **Removed** (a constraint is no longer applicable because the variable no longer exists).
2. Write the updated constraint set. Every updated, added, or removed constraint must include a change justification in the version metadata.
3. Run the Constraint Validator (GAP‑32) against the updated constraint set. All syntax, semantic, logical, performance, and compatibility errors must be resolved.
4. Run the Dependency Analyzer (GAP‑16) against the updated constraint set. Review all impact chains and circular dependencies.
5. Run the Consistency Checker (GAP‑24) against the updated constraint set. Resolve all contradictions and redundancies.

**Output:** Updated constraint set, validated and dependency‑checked.

**Gate:** The constraint owner and compliance officer must both sign off on the updated constraint set before proceeding.

---

### Stage 3 — Pre‑Deployment Testing

**Who:** Model owner + Constraint owner
**What:** Test the updated constraint set against the new model version.

**Required actions:**
1. Deploy the new model version and the updated constraint set in a staging environment.
2. Run the Simulation Engine (GAP‑33) against historical decisions using the new model and the updated constraints. The simulation must show:
   - No unexpected decision changes (ALLOW→BLOCK or BLOCK→ALLOW) unless they are justified by the constraint updates.
   - Approval rate change within acceptable thresholds (configurable, default ±5%).
3. Run the Canary Deployment Manager (GAP‑17) in staging to simulate progressive rollout.
4. If the simulation shows any unexpected decision changes, the constraint set must be revised and re‑tested. Do not proceed to deployment until the simulation passes.

**Output:** Simulation Report, signed by both the model owner and constraint owner.

**Gate:** The simulation report must show GREEN or YELLOW risk level. RED risk level requires revision.

---

### Stage 4 — Deployment

**Who:** Operator + Constraint owner
**What:** Deploy the updated constraint set alongside the new model version.

**Required actions:**
1. Create a new constraint version using the Version Controller (GAP‑15). The version metadata must reference:
   - The model version this constraint set is compatible with.
   - The Impact Assessment Record from Stage 1.
   - The constraint changes from Stage 2.
   - The Simulation Report from Stage 3.
2. Deploy the constraint set using the Canary Deployment Manager (GAP‑17). Start at 1% traffic and monitor for at least 5 minutes at each stage.
3. Monitor the SLA Manager (GAP‑25) for any latency violations during deployment.
4. If any anomaly is detected during canary deployment, roll back immediately and return to Stage 2.

**Output:** Deployment record, including canary stage results and final metrics.

---

### Stage 5 — Post‑Deployment Verification

**Who:** Compliance officer + Auditor
**What:** Verify that the deployed constraint set is correctly enforcing the updated model.

**Required actions:**
1. Export the audit log for the first 24 hours of operation with the new model version and constraint set.
2. Verify that all decisions are correctly signed and that the audit chain is intact.
3. Verify that the constraint version recorded in each decision matches the deployed version.
4. Run the Staleness Detector (GAP‑48) to confirm all constraints are within their review window.
5. Archive the complete governance record for this model version change:
   - Impact Assessment Record
   - Updated constraint set with change justifications
   - Validator, Dependency Analyzer, and Consistency Checker reports
   - Simulation Report
   - Canary deployment metrics
   - Post‑deployment audit log verification

**Output:** Archived governance record, retained for the duration of the model's operational life plus the regulatory retention period (default 7 years).

---

## 4. ROLES AND RESPONSIBILITIES

| Role | Responsibility |
|------|---------------|
| Model Owner | Declares model changes, provides model documentation, participates in impact assessment |
| Constraint Owner | Reviews and updates constraints, runs validation tools, participates in testing |
| Compliance Officer | Approves constraint changes, verifies regulatory alignment, signs off on governance records |
| Operator | Executes deployment, monitors canary stages, responds to deployment alerts |
| Auditor | Verifies post‑deployment audit logs, archives governance records |

In a single‑person deployment, one individual holds all five roles. This is documented as a prototype exception. Before production deployment with a regulated client, the model owner and constraint owner roles must be separated.

---

## 5. MODEL CHANGE REGISTER

Every model version change must be recorded in the Model Change Register with the following fields:

| Field | Description |
|-------|-------------|
| Change ID | Unique identifier for this change |
| Model name | Name of the AI model |
| Old version | Previous model version |
| New version | New model version |
| Change description | What changed in the model |
| Constraints affected | List of constraint identities affected |
| Impact Assessment | Link to the signed Impact Assessment Record |
| Simulation Report | Link to the Simulation Report |
| Deployment date | When the change was deployed |
| Deployed constraint version | The constraint version deployed alongside this model |
| Post‑deployment verification | Date the post‑deployment verification was completed |
| Archived governance record | Link to the complete archived record |

---

## 6. EMERGENCY MODEL ROLLBACK

If a model update causes critical failures (e.g., the extraction schema breaks, causing all decisions to return MISSING_VARIABLE), the operator may execute an emergency rollback without completing all five stages.

**Emergency rollback procedure:**
1. Stop the gateway or revert to the previous constraint version using the Version Controller (GAP‑15).
2. Revert the model to the previous version.
3. Log the emergency rollback in the incident log with the reason.
4. Within 24 hours, complete a retrospective Impact Assessment and file it with the governance record.
5. The compliance officer must review the emergency rollback within 7 days.

Emergency rollbacks are auditable. Every emergency rollback must be justified in the governance record.

---

## 7. COMPLIANCE ALIGNMENT

This governance protocol is designed to satisfy the following regulatory and standards requirements:

| Framework | Requirement | How UICP satisfies it |
|-----------|------------|----------------------|
| EU AI Act Art. 17 | Quality management system for high‑risk AI | Five‑stage gated workflow with auditable records at each stage |
| NIST AI RMF Govern 2.0 | Organisational governance of AI systems | Defined roles, change register, emergency procedures |
| ISO/IEC 42001 Cl. 8.1 | Operational planning and control | Documented procedures for model changes, testing, and deployment |
| SOC 2 CC3.1 | Change management controls | Impact assessment, testing, approval gates, post‑deployment verification |

---

## 8. RELATIONSHIP TO OTHER UICP DOCUMENTS

- **Incident Response Procedure (GAP‑32):** Emergency model rollback is a specific type of incident covered by this document and cross‑referenced in the IRP.
- **Version Control & Rollback (GAP‑15):** Provides the technical mechanism for constraint versioning and rollback referenced throughout this document.
- **Constraint Validator (GAP‑32):** Used at Stage 2 to validate updated constraint sets.
- **Simulation Engine (GAP‑33):** Used at Stage 3 to test constraints against historical decisions.
- **Canary Deployment (GAP‑17):** Used at Stage 4 for progressive rollout.

---

## 9. PROTOTYPE EXCEPTION

In the current pilot deployment, a single individual may hold all five roles defined in Section 4. This exception must be resolved before any regulated production deployment. The separation of model owner and constraint owner roles is the minimum requirement for production.

---

## 10. REVIEW CADENCE

This governance protocol must be reviewed:

- Annually.
- When a new regulatory framework applicable to the deploying organisation comes into force.
- When UICP introduces new governance tools (e.g., automated constraint‑to‑model compatibility checking).

**Next scheduled review:** June 2027

---

**END OF MODEL VERSION GOVERNANCE**
