```markdown
# UICP System Bible — Part 4: Operations

**Version 1.0 — June 2026**
**Audience:** Operators, DevOps engineers, compliance officers, and anyone
responsible for keeping UICP running in production.

---

This document assumes UICP is deployed as a Docker container on a Linux
server or cloud VM. The container exposes two endpoints — `/health` and
`/enforce` — and logs all requests to stdout. If your deployment differs,
adjust the commands accordingly. The principles remain the same.

---

## 1. DAILY OPERATIONS

Every day, an operator should perform these checks. They take less than
five minutes total.

### 1.1 Health Check

```bash
curl http://localhost:5000/health
```

Expected response: {"status":"healthy"} and HTTP status 200.

If the response is anything else, or if the request times out, the
container may be down. Follow the incident response procedure in
Section 5.

1.2 Container Status

```bash
docker ps --filter "name=uicp"
```

The container should show as Up. If it is not running:

```bash
docker start uicp
```

If the container is repeatedly restarting, check the logs:

```bash
docker logs uicp --tail 50
```

Look for FATAL STARTUP ERROR messages. Common causes:

· CONSTRAINT_SET_PATH environment variable not set or pointing to a
  missing file.
· API_KEY environment variable not set.
· Constraint set file is not valid JSON.
· Personal data store encryption key is not 64 hex characters.

1.3 Recent Logs

```bash
docker logs uicp --since 1h
```

Review for:

· Requests returning 500 or 503 status codes.
· error_type values other than null.
· Any log lines containing FATAL or CRITICAL.

1.4 Disk Space

```bash
df -h /var/lib/docker
```

The audit log and personal data store grow over time. Ensure at least
20% disk space is free. If disk usage exceeds 80%, trigger an audit
log archive (see Section 7).

---

2. MONITORING

UICP exposes a health endpoint that should be monitored continuously.
Any monitoring system that supports HTTP checks can be used.

2.1 Health Check Monitor

Configure your monitoring system (Nagios, Prometheus, Datadog, or a
simple cron job) to call GET /health every 60 seconds.

Alert if:

· The health check fails for 2 consecutive attempts.
· Response time exceeds 5 seconds.

2.2 Log‑Based Alerts

If you are shipping logs to a central system (ELK, Loki, CloudWatch),
set up alerts for:

· GATEWAY_UNAVAILABLE appearing in any log line — indicates the
  fail‑safe activated and decisions are being blocked.
· Error rate exceeding 1% of total requests in any 5‑minute window.
· Latency p99 exceeding 500ms for enforcement decisions — indicates
  a performance degradation.

2.3 Audit Bundle Verification

Once per week, export the audit bundle and run the standalone verifier:

```bash
python3 verify_uicp_bundle.py audit_export/ public_keys.json
```

If verification fails, the audit chain may be compromised. Follow the
incident response procedure immediately.

---

3. INCIDENT RESPONSE

3.1 Gateway Unavailable (Severity 1 — Critical)

Symptoms:

· /health returns non‑200 status or times out.
· /enforce returns {"status":"GATEWAY_UNAVAILABLE"} for all requests.
· Container is not running.

Response:

1. Check container status: docker ps -a | grep uicp
2. If stopped, start it: docker start uicp
3. If it fails to start, check logs: docker logs uicp --tail 100
4. Common fixes:
   · Missing constraint file: Verify the file exists at the path
     specified by CONSTRAINT_SET_PATH. If it was accidentally deleted,
     restore from backup.
   · Invalid JSON: If the constraint file was edited manually, check
     for syntax errors: python3 -m json.tool constraint_set.json
   · Disk full: Free space by archiving old audit logs (Section 7).
   · Port conflict: Ensure no other process is using port 5000.
5. If the container starts but /health still fails, restart it:
   ```bash
   docker restart uicp
   ```
6. If the issue persists after restart, deploy a new container from the
   latest Docker image.

While the gateway is unavailable:

· Route all decisions to manual review. Do NOT allow decisions to proceed
  without human approval.
· Notify the compliance officer and any affected clients within 1 hour.

3.2 Unexpected BLOCK Rate (Severity 2 — High)

Symptoms:

· BLOCK rate increases by more than 20% compared to the 7‑day average.
· Constraints that were consistently passing are now failing.

Response:

1. Check whether the extraction schema is still correctly parsing model
   outputs. The model's output format may have changed. Test extraction
   against 10‑20 recent model outputs manually.
2. Check whether the constraint set was recently updated. If a constraint
   change caused the increase, roll back to the previous version.
3. Check whether the model itself has been retrained or replaced. A new
   model version may produce outputs in a different format.
4. If the BLOCK rate increase is unexplained, export the last 50 BLOCK
   decisions and review the violation details. Look for patterns — is
   a single constraint responsible for most blocks?

3.3 Key Compromise (Severity 1 — Critical)

Symptoms:

· A signing key has been exposed in logs, error messages, or source code.
· An unauthorised party has access to a private key.

Response:

1. Revoke the compromised key immediately using the Key Lifecycle Manager.
2. Generate a new key pair.
3. Re‑sign all constraint commitments with the new key.
4. Notify all verifiers that the old key is revoked.
5. Audit all decisions signed with the compromised key to confirm no
   forged decisions exist.
6. Document the incident, including how the key was exposed and what
   steps prevent recurrence.

---

4. KEY MANAGEMENT

4.1 Key Storage

· Development: Keys are generated in memory and discarded when the
  session ends. Acceptable for testing only.
· Staging: Keys are stored in an AES‑256‑GCM encrypted file. The
  encryption key is in the KEY_ENCRYPTION_KEY environment variable —
  never in the same file as the data.
· Production: Keys MUST be stored in a Hardware Security Module (HSM)
  or equivalent Key Management Service (AWS KMS, Azure Key Vault, Google
  Cloud KMS). Private keys must never be written to disk.

4.2 Key Rotation

Rotate signing keys every 12 months, or immediately upon suspected
compromise.

1. Generate a new key pair.
2. Register the new public key in the Operator Registry.
3. Call rotate() on the old key — it becomes ROTATED. Historical
   signatures remain verifiable.
4. Update all consuming systems with the new key ID.
5. Record the rotation event in the audit log.

4.3 Emergency Revocation

If a key is compromised:

1. Call revoke(key_id, reason) immediately.
2. The reason must be specific — e.g., "Key exposed in CI pipeline logs
   on 2026‑06‑15."
3. All signatures from the revoked key will be rejected from that moment
   forward.
4. Generate a replacement key and re‑register it.
5. Document the revocation in the incident log.

---

5. CONSTRAINT UPDATES

5.1 Updating Constraints (Container Restart)

1. Edit the constraint set JSON file.
2. Run the Constraint Validator to check for syntax errors,
   contradictions, and missing variables.
3. Run the Simulation Engine against a sample of recent decisions to
   preview the impact of the change.
4. If the simulation shows acceptable impact, restart the container:
   ```bash
   docker restart uicp
   ```
5. Verify that /health returns healthy and /enforce returns correct
   decisions for a known test case.

5.2 Rolling Back Constraints

1. Restore the previous version of the constraint set JSON file from
   version control or backup.
2. Restart the container.
3. Verify as above.

5.3 Canary Deployment

For high‑stakes constraint changes, use the Canary Deployment Manager
to progressively roll out the new constraint set across a percentage
of traffic, monitoring metrics at each stage. If the approval rate
drops or error rate spikes, the deployment is automatically rolled
back.

---

6. BACKUP AND RESTORE

6.1 What to Back Up

Asset Frequency Location
Constraint set JSON After every update Version control (Git)
Audit log (PostgreSQL) Nightly + hourly incremental S3 or equivalent
Personal data store (encrypted) Nightly S3 or equivalent
Signing keys (encrypted) After every rotation Separate secure storage
Docker image After every build Container registry

6.2 Restoring the Audit Log

1. Restore the PostgreSQL backup to a new database.
2. Verify the cryptographic chain integrity using the verification
   script.
3. Point the UICP container to the restored database (if the audit log
   is stored externally) or replace the audit log file.

6.3 Restoring the Constraint Set

1. Check out the desired version from Git.
2. Place the file at the path specified by CONSTRAINT_SET_PATH.
3. Restart the container.

---

7. AUDIT LOG ARCHIVAL

Audit logs grow continuously. To manage disk space and maintain query
performance:

1. Run the Archival Manager monthly to archive logs older than 90 days
   to S3 or equivalent object storage.
2. Archived logs are compressed (70‑80% size reduction) and checksummed.
3. Verify one random archive per quarter by restoring it to a test
   database and checking record integrity.
4. Purge archives older than the retention period (default 7 years for
   financial compliance, configurable per tenant).

---

8. DISASTER RECOVERY

8.1 Recovery Objectives

· Recovery Time Objective (RTO): Restore service within 4 hours.
· Recovery Point Objective (RPO): Lose no more than 1 hour of data.

8.2 Complete Server Failure

If the server hosting UICP fails completely:

1. Provision a new server or cloud VM.
2. Install Docker.
3. Pull the latest UICP Docker image.
4. Restore the constraint set JSON file from Git.
5. Restore the audit log from the most recent backup.
6. Restore the signing keys from secure storage.
7. Start the container with the same environment variables.
8. Verify with /health and a test enforcement call.

8.3 Database Corruption

1. Stop the UICP container.
2. Restore the database from the most recent backup (nightly full +
   hourly incremental).
3. Verify the cryptographic chain integrity.
4. Restart the container.

8.4 Ransomware or Malicious Deletion

If the audit log or constraint files are encrypted or deleted by an
attacker:

1. Isolate the affected server immediately.
2. Provision a clean server.
3. Restore all data from backups — do NOT attempt to recover encrypted
   files.
4. Rotate all signing keys — assume they may have been accessed.
5. Audit the restored audit log for any decisions made during the
   compromise window.

---

9. NEXT IN THE SYSTEM BIBLE

· Part 5 — Governance: NIST AI RMF alignment, GDPR compliance, SOC 2
  Type II audit plan, EU AI Act mapping.
· Part 6 — Business: Pricing, contracts, intellectual property,
  engine protection doctrine, and client offboarding.

```
