# UICP Business Continuity & Disaster Recovery Plan

## Version 1.0 — Pilot‑Ready
### Status: Active
### Audience: Operators, IT Administrators, Compliance Officers

---

## 1. PURPOSE

This document defines the procedures for maintaining or restoring UICP enforcement operations during and after a disruption. It covers two scenarios:

- **Business Continuity (BC):** Keeping UICP running during minor to moderate disruptions (server failure, network outage, application crash).
- **Disaster Recovery (DR):** Restoring UICP operations after a major disruption (data centre loss, ransomware, complete system failure).

Every operator must know exactly what to do when the system fails — without calling the developer, without panic, and with a clear, tested recovery path.

---

## 2. RECOVERY OBJECTIVES

UICP commits to the following recovery targets:

| Metric | Target | Definition |
|--------|--------|-----------|
| Recovery Time Objective (RTO) | 4 hours | Maximum acceptable time to restore enforcement operations after a disaster |
| Recovery Point Objective (RPO) | 1 hour | Maximum acceptable data loss measured in time (audit log entries lost after last backup) |
| Maximum Tolerable Downtime (MTD) | 8 hours | Maximum time UICP can be unavailable before business impact becomes unacceptable |

These targets apply to Severity 1 incidents as defined in the Incident Response Procedure. The RTO assumes that replacement infrastructure is available (a new VM can be provisioned, Docker installed, and the container restarted within 4 hours).

---

## 3. BUSINESS CONTINUITY PROCEDURES

### 3.1 Container Failure

If the UICP Docker container crashes or stops responding:

1. Check container status: `docker ps -a --filter name=uicp`
2. If the container is stopped: `docker start uicp`
3. Verify health: `curl http://localhost:5000/health`
4. If the container fails to start, check logs: `docker logs uicp --tail 50`
5. If the container is corrupted, rebuild from image: `docker build -t uicp-gateway . && docker run -d --name uicp ...`

**Expected recovery time:** 5 minutes

### 3.2 Host Server Failure

If the host server fails (hardware failure, kernel panic, out‑of‑memory):

1. Provision a replacement server (cloud: launch a new VM from the most recent snapshot; on‑premises: use a standby server).
2. Install Docker on the replacement server.
3. Copy the constraint file and encryption key from secure backup to the replacement server.
4. Run the Docker container with the same environment variables and volume mounts.
5. Verify health check and run a test enforcement request.

**Expected recovery time:** 1 hour (with pre‑provisioned standby) to 4 hours (provisioning a new VM from scratch)

### 3.3 Database Failure (PostgreSQL)

If the PostgreSQL audit database fails:

1. Check database connectivity: `docker exec uicp python -c "import psycopg2; psycopg2.connect('...')"`
2. If the database is down, restart it: `docker restart postgres`
3. If the database is corrupted, restore from the most recent backup using `pg_restore`.
4. Verify that UICP can write new decisions to the restored database.

**Expected recovery time:** 30 minutes (restart) to 2 hours (full restore)

### 3.4 Constraint File Corruption

If the constraint file becomes corrupted or invalid:

1. UICP will fail to start or will return GATEWAY_UNAVAILABLE for all requests.
2. Restore the constraint file from the most recent backup or version control.
3. Restart the container: `docker restart uicp`
4. Verify health and run a test enforcement request.

**Expected recovery time:** 10 minutes

---

## 4. DISASTER RECOVERY PROCEDURES

### 4.1 Complete Data Centre Loss

If the physical or cloud data centre hosting UICP is completely lost (fire, natural disaster, ransomware, provider outage):

1. **Activate the disaster recovery plan.** The decision to declare a disaster is made by the incident lead.
2. **Provision replacement infrastructure** in a different availability zone or region (cloud) or at the designated DR site (on‑premises).
3. **Restore from backups** in this order:
   a. Constraint file and encryption keys (from secure, off‑site backup).
   b. PostgreSQL audit database (from the most recent `pg_dump` backup).
   c. Docker image (rebuild from source or pull from container registry).
4. **Start UICP** on the replacement infrastructure using the restored files and database.
5. **Validate:** run the full test suite (73/73 enforcement, 101/101 audit) against the restored system. Send a test enforcement request and verify ALLOW/BLOCK behaviour.
6. **Update DNS** to point to the new deployment if the IP address has changed.
7. **Notify affected clients** using the Severity 1 communication template from the Incident Response Procedure.
8. **Log the disaster declaration and recovery actions** in the incident log.

**Expected recovery time:** 4 hours (RTO)

### 4.2 Ransomware or Malicious Encryption

If UICP's host or data is encrypted by ransomware:

1. **Immediately isolate the affected system.** Disconnect it from the network. Do NOT pay the ransom.
2. **Provision a clean replacement system** (do not attempt to clean the infected one).
3. **Restore from clean backups** as described in Section 4.1.
4. **Investigate the attack vector** (how did the ransomware enter?). Patch the vulnerability before restoring service.
5. **Notify the Data Protection Officer** if personal data was potentially exposed (GDPR Article 33 breach notification).

### 4.3 Total Encryption Key Loss

If all copies of the encryption key are lost (the key protecting the personal data store):

1. The personal data store becomes permanently inaccessible. This is a data loss event, not a service outage.
2. UICP can continue to enforce constraints because the enforcement engine does not depend on the personal data store.
3. Historical audit log hashes remain verifiable.
4. Notify the DPO immediately. This constitutes a personal data breach if personal data was stored and is now unrecoverable.
5. Generate a new encryption key for future personal data.

---

## 5. BACKUP STRATEGY

### 5.1 What Is Backed Up

| Asset | Backup Method | Frequency | Retention | Storage Location |
|-------|--------------|-----------|-----------|-----------------|
| Constraint file | Version control (Git) + encrypted file copy | On every change | Indefinite | GitHub + off‑site encrypted backup |
| Encryption keys | Encrypted export + secure offline storage | On generation and rotation | Indefinite | Off‑site, separate from data backups |
| PostgreSQL audit database | `pg_dump` | Hourly | 30 days rolling | Separate cloud region or on‑premises server |
| Docker image | Container registry or source rebuild | On release | Indefinite | GitHub + container registry |

### 5.2 Backup Verification

Backups must be tested:

- **Monthly:** Restore the most recent database backup to a test instance and verify that the audit log is queryable.
- **Quarterly:** Perform a full disaster recovery test — provision a new VM, restore all backups, start UICP, and run the full test suite.
- **Annually:** Perform a disaster recovery test from the off‑site backup location to simulate a complete data centre loss.

Test results must be documented and retained for compliance audits.

---

## 6. FAILOVER AND REDUNDANCY

### 6.1 Current State (Pilot)

In the pilot deployment, UICP runs as a single Docker container with a single PostgreSQL database. There is no automatic failover. If the container or host fails, the operator must manually follow the recovery procedures in Section 3.

### 6.2 Post‑Pilot (GAP‑20)

After GAP‑20 (Redundancy) is fully implemented:

- Multiple UICP instances run behind a load balancer (nginx).
- If one instance fails, the load balancer routes traffic to healthy instances.
- The PostgreSQL database should be deployed in a high‑availability configuration (primary‑standby replication) to enable automatic failover.
- The Recovery Time Objective (RTO) can be reduced from 4 hours to under 5 minutes for most failure scenarios.

---

## 7. ROLES AND RESPONSIBILITIES

| Role | Responsibility |
|------|---------------|
| Incident Lead | Declares a disaster, coordinates recovery |
| Operator | Executes recovery procedures, restores backups |
| IT Administrator | Provisions replacement infrastructure, configures networking |
| DPO | Assesses data breach impact, notifies supervisory authority if required |

In a single‑operator deployment, one person holds all roles. This is documented as a prototype exception.

---

## 8. TESTING AND MAINTENANCE

This plan must be tested:

- **Quarterly:** Tabletop exercise — walk through the disaster recovery procedures with the operations team. Identify gaps and update the plan.
- **Annually:** Full live test — simulate a complete data centre loss and restore UICP from backups within the RTO.

After any real disaster recovery event, a post‑incident review must be conducted and this plan updated with lessons learned.

---

## 9. DEPENDENCIES

UICP's recovery depends on the availability of:

- Docker (open‑source, no vendor dependency).
- PostgreSQL (open‑source, no vendor dependency).
- Python 3.12 (open‑source, no vendor dependency).
- The `cryptography` and `Flask` Python packages (open‑source, pinned versions in `requirements.txt`).

UICP has no dependency on any proprietary service or vendor for its core enforcement operation. This eliminates vendor lock‑in as a recovery risk.

---

## 10. REVIEW CADENCE

This plan must be reviewed and updated:

- Annually.
- After any disaster recovery event.
- When the deployment architecture changes (e.g., adding Kubernetes, multi‑region).
- When recovery time objectives are renegotiated with a client.

**Next scheduled review:** June 2027

---

**END OF BUSINESS CONTINUITY & DISASTER RECOVERY PLAN**
