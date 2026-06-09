
# UICP Incident Response Procedure

## Version 1.0 — Pilot‑Ready
### Status: Active
### Audience: Operators, Compliance Officers, Security Teams

---

## PURPOSE

This document defines the step‑by‑step procedures for detecting, containing, investigating, recovering from, and reporting security and operational incidents involving the UICP enforcement gateway. Every operator must know exactly what to do when something goes wrong — without calling the developer, without panic, and with a clear audit trail.

---

## INCIDENT SEVERITY LEVELS

UICP incidents are classified into three severities based on impact.

**SEVERITY 1 — CRITICAL**
- The enforcement gateway is completely down or returning incorrect decisions (false ALLOW or false BLOCK) for all tenants.
- A signing key has been confirmed or strongly suspected compromised.
- The audit log has been tampered with or is unreachable.
- *Response time target: Begin containment within 15 minutes of detection. Patch within 48 hours for security defects, 72 hours for enforcement defects.*

**SEVERITY 2 — WARNING**
- A single tenant's constraint set is causing excessive BLOCKs (over‑blocking) or missed violations (under‑blocking).
- Latency exceeds SLA thresholds for more than 5 minutes.
- A non‑critical service (e.g., the simulation engine or dependency analyzer) is unavailable.
- *Response time target: Begin investigation within 1 hour of detection.*

**SEVERITY 3 — INFO**
- A non‑critical bug is discovered (documentation error, minor UI issue, log formatting).
- A constraint staleness alert fires for a single constraint.
- *Response time target: Address in the next scheduled maintenance window.*

---

## INCIDENT RESPONSE WORKFLOW

Every incident follows this five‑phase workflow regardless of severity.

### Phase 1 — Detection (0–15 minutes)

**How incidents are detected:**
- Automated health‑check failures (the `/health` endpoint returns non‑200 or times out).
- Alert manager notifications (GAP‑50) triggered by anomaly detection.
- Operator observation during daily monitoring.
- Client report.

**First responder actions:**
1. Confirm the incident is real — run `curl http://localhost:5000/health` from the host. If the health check passes, the gateway is running; investigate upstream.
2. Check `docker ps` to confirm the container is running.
3. Check `docker logs uicp --tail 50` for error messages.
4. Determine severity using the definitions above.
5. Log the detection time, severity, and initial observations in the incident log.

### Phase 2 — Containment (15 minutes–1 hour)

**For Severity 1 (critical):**
1. If the gateway is returning false ALLOW decisions, stop the container immediately: `docker stop uicp`. The absence of the gateway means all decisions are blocked by the orchestrator's fail‑safe.
2. If a signing key is compromised, revoke it immediately using the KeyLifecycleManager (GAP‑13/14). Notify the key registry.
3. If the audit log is tampered with, export the current state immediately for forensic analysis: `docker cp uicp:/app/audit_export ./forensic_snapshot`. Do not restart the container until the snapshot is taken.
4. Notify affected clients within 1 hour. The notification must include: the nature of the incident, the containment actions taken, the expected impact on their operations, and the estimated time to resolution.

**For Severity 2 (warning):**
1. If over‑blocking is detected, temporarily revert to the previous constraint version using the VersionController (GAP‑15): `rotate_constraints.py rollback --deployment <id> --reason "Over‑blocking detected"`.
2. If latency is degraded, check host resource usage (`top`, `df -h`). Restart the container if resources are normal but latency remains high.
3. Notify affected clients if the warning condition persists for more than 1 hour.

**For Severity 3 (info):**
- No immediate containment required. Log the incident and schedule a fix.

### Phase 3 — Investigation (1–24 hours)

1. Export the full audit log for the affected period: `python3 decision_export.py`.
2. Review the log for anomalies: sudden changes in decision rates, unusual constraint violations, signature verification failures.
3. If the incident involves a specific constraint set, run the simulation engine (GAP‑33) against historical decisions with the suspect constraint to reproduce the issue.
4. If the incident involves a crash, review the container logs and any core dumps.
5. Document the root cause. If the root cause cannot be determined within 24 hours, escalate to the UICP development team.

### Phase 4 — Recovery (24 hours–ongoing)

1. Apply the fix: patch the defect, update the constraint set, rotate the key, or restore the audit log from backup.
2. Validate the fix: run the full test suite (73/73 enforcement, 101/101 audit, 14/14 API) before returning the gateway to production.
3. If the fix involves a constraint change, run the Constraint Validator (GAP‑32) and the Simulation Engine (GAP‑33) against the new constraint set before deployment.
4. Deploy the fix using the canary deployment manager (GAP‑17). Start at 1% traffic and monitor for 5 minutes before advancing.
5. Restore service and confirm the health check passes.
6. Notify affected clients that service is restored.

### Phase 5 — Post‑Incident Review (within 7 days)

1. Write a post‑incident report covering: timeline of events, root cause analysis, containment and recovery actions taken, impact assessment (number of decisions affected, clients impacted), lessons learned, and preventive measures implemented.
2. Update this incident response procedure if the incident revealed gaps in the existing process.
3. If the incident involved a defect in UICP itself, add a regression test to the test suite to prevent recurrence.
4. Archive the post‑incident report in the audit log for future compliance audits.

---

## INCIDENT‑SPECIFIC PROCEDURES

### False ALLOW (constraint violation not detected)

**How to detect:** A client reports that a decision was allowed despite violating a documented constraint. Or, a compliance audit finds a violation in the audit log that was marked ALLOW.

**Immediate action:**
1. Stop the gateway immediately. False ALLOW means the system is not enforcing constraints — every decision is suspect until resolved.
2. Export the audit log covering the period when the false ALLOW occurred.
3. Identify the specific constraint that was not enforced and the specific binding values that should have triggered a BLOCK.
4. Run the constraint validator (GAP‑32) against the constraint set to check for errors.
5. Patch the defect or update the constraint. Validate with the test suite.
6. Restart with canary deployment (GAP‑17).

### False BLOCK (valid output incorrectly rejected)

**How to detect:** Client complaint or a sudden, unexplained drop in approval rate.

**Immediate action:**
1. Check the audit log for the most frequently violated constraint.
2. Temporarily revert to the previous constraint version (GAP‑15).
3. Investigate whether the constraint was incorrectly defined (e.g., wrong threshold) or whether the binding extraction is producing incorrect values.
4. Fix the root cause, test, and redeploy.

### Signing Key Compromise

**How to detect:** Alert manager notification (unexpected signature verification failures). Or, discovery of the private key in an unprotected location (logs, environment variables, unencrypted backup).

**Immediate action:**
1. Revoke the key immediately using the KeyLifecycleManager (GAP‑13/14).
2. Generate a new key pair.
3. Re‑sign all active constraints with the new key.
4. Notify all verifiers (clients, auditors) that the old key is revoked and provide the new public key.
5. Investigate how the key was compromised. Secure the deployment environment. Document the incident for compliance.

### Audit Log Tampering

**How to detect:** The `verify_chain_integrity()` method returns `False`. Or, the manifest export ID does not match the computed SHA‑256 of the chain files.

**Immediate action:**
1. Export the current audit log state immediately (`forensic_snapshot`).
2. Compare the current state against the most recent verified export to identify which records were modified.
3. Restore the audit log from the most recent clean backup.
4. Investigate how tampering occurred (compromised host, insider threat, software defect).
5. If tampering cannot be explained, treat the host as compromised and rebuild from a clean image.

---

## COMMUNICATION TEMPLATES

### Client Notification — Severity 1

```

Subject: URGENT — UICP Enforcement Incident — [Client Name]

Dear [Client Name],

At [timestamp], UICP detected a critical incident affecting constraint
enforcement for your tenant.

Nature of incident: [brief description]
Impact: [ALLOW/BLOCK decisions affected, time period]
Containment action taken: [what we did — e.g., "gateway stopped, manual review activated"]
Estimated resolution time: [ETA]

We will update you within [next update window, e.g., 2 hours] or immediately
upon resolution.

If you need to activate your manual review process, please contact [client's
own ops contact].

Yours sincerely,
UICP Operations

```

### Post‑Incident Report Template

```

Post‑Incident Report — [Incident ID]

Date of incident: [date]
Time detected: [timestamp]
Time resolved: [timestamp]
Severity: [1/2/3]

Timeline

· [HH:MM] Incident detected by [method]
· [HH:MM] Containment actions initiated
· [HH:MM] Root cause identified
· [HH:MM] Fix deployed and validated
· [HH:MM] Service restored

Root Cause

[Technical explanation of what went wrong]

Impact

· Tenants affected: [list]
· Decisions affected: [number or "all"]
· False ALLOW count: [number]
· False BLOCK count: [number]

Lessons Learned

[What we will change to prevent recurrence]

Preventive Measures

· Add regression test
· Update documentation
· Update monitoring thresholds
· Train operators

Report prepared by: [name]
Reviewed by: [name]
Date: [date]

```

---

## ROLES AND RESPONSIBILITIES

| Role | Responsibility |
|------|---------------|
| First Responder | Detect, log, and contain the incident |
| Incident Lead | Coordinate investigation, communicate with clients |
| Operator | Execute containment actions (stop/start gateway, rollback constraints) |
| Auditor | Export and verify audit logs, provide forensic evidence |
| Developer | Investigate root cause, produce patch, validate fix |

In a single‑operator deployment (prototype/pilot), one person holds all roles. This must be documented as a prototype exception. Before production deployment with a paying client, the first responder and incident lead roles must be separated.

---

## TRAINING REQUIREMENTS

Before an operator is authorised to respond to incidents, they must:

1. Read this procedure in full.
2. Successfully contain a simulated Severity 2 incident in a staging environment (e.g., deliberate over‑blocking from a bad constraint).
3. Successfully restore the gateway from a simulated audit log tampering event.
4. Demonstrate the ability to export and verify an audit bundle using the public verification scripts.

Training records must be kept and made available to auditors.

---

## REVIEW CADENCE

This procedure must be reviewed and updated:

- Quarterly (every 3 months).
- After any Severity 1 incident.
- When a new component is added to the UICP pipeline.
- When a new operator joins the team.

**Next scheduled review:** [Insert date 3 months from now]

---

**END OF INCIDENT REPORT
