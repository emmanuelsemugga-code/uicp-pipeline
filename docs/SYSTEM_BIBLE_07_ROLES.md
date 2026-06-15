```markdown
# UICP System Bible — Part 7: Roles

**Version 1.0 — June 2026**
**Audience:** Business planners, grant committees, hiring managers,
and anyone building the team that will operate UICP at scale.

---

This document defines every job role required to operate UICP from
pilot phase through enterprise scale. Each role includes: what the
person does, the skills they need, when to hire them, and the
monthly salary range for Uganda‑based hires.

All salaries are in Ugandan shillings (UGX) and are based on Kampala
market rates for technology professionals as of June 2026.

---

## 1. UICP SUPPORT ENGINEER

**When to hire:** First paying client (immediately after pilot converts).

**What they do:**
- Monitor the UICP gateway health endpoint daily.
- Respond to client support requests within the SLA timeline.
- Troubleshoot extraction failures, constraint evaluation errors, and
  API authentication issues.
- Escalate unresolved issues to the founder or senior engineer.
- Maintain the support knowledge base — document every resolved issue.
- Run weekly audit bundle verification.

**Skills required:**
- Python (basic — can read logs, run scripts, edit JSON files).
- Docker (basic — can check container status, restart containers,
  read logs).
- REST APIs (basic — can use `curl` to test endpoints).
- Git (basic — can clone a repository, check out a branch).
- Strong written communication (most support is email‑based).

**Salary range:** UGX 3,000,000–5,000,000 per month.

**How to find this person:** Recent computer science or IT graduate
from Makerere, Kyambogo, or MUBS. Train them for two weeks on UICP
specifically. This is an entry‑level role that grows with the company.

---

## 2. UICP DEVOPS ENGINEER

**When to hire:** Five paying clients, or when the first Enterprise
client signs.

**What they do:**
- Deploy and manage UICP Docker containers across client environments.
- Set up monitoring, alerting, and log aggregation.
- Manage database backups, audit log archival, and disaster recovery
  testing.
- Automate constraint set deployment and rollback.
- Maintain the CI/CD pipeline for UICP engine updates.
- Manage signing key infrastructure (generation, rotation, revocation,
  secure storage).

**Skills required:**
- Docker and container orchestration (strong).
- Linux system administration (strong).
- Cloud platforms (AWS, GCP, or Azure — at least one).
- PostgreSQL administration (backup, restore, replication).
- Monitoring tools (Prometheus, Grafana, or equivalent).
- Shell scripting and Python (intermediate).
- Information security fundamentals (key management, encryption at
  rest, TLS).

**Salary range:** UGX 5,000,000–8,000,000 per month.

**How to find this person:** Mid‑career DevOps engineer currently
working at a Ugandan fintech, telecom, or cloud provider. Look for
someone with 3‑5 years of experience who wants to work on AI
infrastructure.

---

## 3. COMPLIANCE AND GOVERNANCE OFFICER

**When to hire:** Before SOC 2 Type II engagement begins (requires
production audit logs from a paying client).

**What they do:**
- Own the SOC 2 Type II audit process — evidence collection, auditor
  liaison, quarterly control testing.
- Maintain the Regulatory Change Register — track regulatory changes
  across all client jurisdictions.
- Review constraint sets for fairness and regulatory compliance.
- Conduct monthly access control reviews.
- Maintain the AI Asset Register — ensure every governed model is
  documented.
- Prepare quarterly NIST AI RMF compliance assessments.
- Manage data subject requests (GDPR Articles 15‑22).

**Skills required:**
- Regulatory compliance (GDPR, NIST AI RMF, ISO 42001, SOC 2).
- Audit management (evidence collection, auditor communication).
- Policy drafting and review.
- Strong written communication (regulatory submissions, client
  notifications).
- Attention to detail (compliance is about what you can prove, not
  what you believe).

**Salary range:** UGX 4,000,000–7,000,000 per month.

**How to find this person:** Compliance officer or risk manager
currently working at a Ugandan bank, insurance company, or
telecommunications provider. They understand regulated environments.
Train them on AI‑specific frameworks (NIST, EU AI Act).

---

## 4. BUSINESS DEVELOPMENT LEAD

**When to hire:** After public launch — when the repository is public,
the demo video is live, and the documentation is complete.

**What they do:**
- Identify and qualify potential pilot partners in lending, healthcare,
  and government.
- Manage the pilot pipeline — from first contact to signed agreement.
- Prepare and deliver proposals, pitches, and demonstrations to
  prospective clients.
- Represent UICP at industry events, conferences, and regulatory
  meetings.
- Manage relationships with existing clients — check‑ins, renewals,
  expansion.
- Track competitor activity and market trends in AI governance.

**Skills required:**
- Enterprise sales or business development (3‑5 years).
- Understanding of financial services, healthcare, or government
  procurement (at least one sector).
- Strong presentation and communication skills.
- Proposal writing and contract negotiation.
- Network in Kampala's business, technology, or government community.

**Salary range:** UGX 4,000,000–8,000,000 per month, plus commission
on signed contracts (5‑10% of first‑year contract value).

**How to find this person:** Business development manager currently
selling enterprise software, fintech solutions, or compliance services
in Uganda. They already know the buyers. They just need to learn the
product.

---

## 5. TECHNICAL WRITER

**When to hire:** Three paying clients — when the volume of
documentation requests, client onboarding, and knowledge base
maintenance exceeds what the founder can handle alone.

**What they do:**
- Maintain the UICP System Bible — update it with every new feature
  and client requirement.
- Write and update client‑facing documentation: onboarding guides,
  API references, troubleshooting guides.
- Maintain the public knowledge base and FAQ.
- Write case studies from pilot and production deployments.
- Prepare grant reports and technical progress updates for funding
  agencies.
- Write the UICP White Paper for academic publication.

**Skills required:**
- Technical writing (2‑3 years — can explain complex systems clearly).
- Markdown and Git (proficient — all UICP documentation is in
  Markdown in the repository).
- Python (basic — can read and understand code, test API endpoints).
- Strong research skills (can verify technical claims before
  publishing).

**Salary range:** UGX 3,000,000–5,000,000 per month.

**How to find this person:** Technical writer currently working at a
Ugandan technology company, telecommunications provider, or
international NGO with a Kampala office. Look for someone who has
written user manuals, API documentation, or training materials.

---

## 6. FOUNDER / CHIEF ENGINEER (Emmanuel Semugga)

**Role until first hires are made:** Everything.

**After first hires:**
- Technical architecture and engine development.
- Adversarial validation and security review.
- Key client relationships and strategic partnerships.
- Grant applications and fundraising.
- Public representation (LinkedIn, conferences, media).

---

## HIRING PRIORITY AND TRIGGERS

| Priority | Role | Trigger | Estimated Timing |
|----------|------|---------|------------------|
| 1 | Support Engineer | First paying client | Month 1‑3 after launch |
| 2 | Business Development Lead | After public launch | Month 1‑2 |
| 3 | Technical Writer | 3 paying clients | Month 3‑6 |
| 4 | DevOps Engineer | 5 clients or first Enterprise | Month 6‑12 |
| 5 | Compliance Officer | Before SOC 2 engagement | Month 6‑12 |

---

## HOW TO HIRE IN UGANDA

1. **Post on LinkedIn** (free) — target Kampala‑based professionals
   with the specific skills listed above.
2. **Contact university career offices** — Makerere, Kyambogo, MUBS —
   for entry‑level roles (Support Engineer).
3. **Ask your network** — the Kampala technology community is small
   and interconnected. A recommendation from someone you trust is
   worth more than a CV.
4. **Use BrighterMonday or Jobberman** for mid‑career roles (DevOps,
   Compliance, BD Lead).
5. **Offer equity or revenue share** if you cannot meet salary bands
   immediately. This is standard for early‑stage Ugandan startups.

---

## NEXT IN THE SYSTEM BIBLE

- **Part 8 — Client‑Facing Resources:** The onboarding checklist, the API
  reference, the knowledge base, and the client intake form.
- **Part 9 — Appendices:** Complete traceability — every GAP closed,
  every test result, every validation run, every adversarial evaluation.
