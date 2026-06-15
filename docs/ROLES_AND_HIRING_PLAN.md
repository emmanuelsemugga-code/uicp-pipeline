```markdown
# UICP — Roles & Hiring Plan

**Version 1.0 — June 2026**
**Audience:** Business planners, grant committees, hiring managers,
and anyone building the team that will operate UICP at scale.

---

This document defines every job role required to operate UICP from
pilot phase through enterprise scale. Each role includes: what the
person does day‑to‑day, the skills and experience they must have,
when to hire them, and the monthly salary range for Uganda‑based hires.

All salaries are in Ugandan shillings (UGX) and are based on Kampala
market rates for technology professionals as of June 2026.

---

## 1. UICP SUPPORT ENGINEER

**When to hire:** First paying client (immediately after pilot converts).

### What They Do Day‑to‑Day

- Monitor the UICP gateway health endpoint every morning and every
  evening. Check that `/health` returns `{"status":"healthy"}` and HTTP 200.
- Respond to client support requests within the SLA timeline (1 business
  day for Standard tier, 4 hours for Enterprise tier).
- Troubleshoot extraction failures — when a client reports that UICP is
  returning `INCOMPLETE` for variables that should be extractable, the
  Support Engineer examines the model output, tests the extraction schema
  against it, and identifies whether the regex pattern, the model output
  format, or the schema configuration is the cause.
- Troubleshoot constraint evaluation errors — when a client reports
  unexpected BLOCK decisions, the Support Engineer examines the violation
  details, checks the constraint set for errors, and determines whether
  the constraint, the extraction, or the model output is at fault.
- Escalate unresolved issues to the founder or senior engineer within 4
  hours if they cannot resolve them independently.
- Maintain the support knowledge base — after every resolved issue, write
  a short article in `docs/KNOWLEDGE_BASE.md` so the same question never
  needs to be answered twice.
- Run weekly audit bundle verification for each active client and confirm
  that all cryptographic checks pass.
- Maintain the system status page (`docs/STATUS_PAGE.md`) — update it
  immediately if the gateway status changes.

### Minimum Skills and Experience

**Must have:**
- Python — can read and understand Python code, run scripts, and edit
  JSON configuration files. Does not need to write production code, but
  must be able to modify extraction schemas and constraint files without
  breaking syntax.
- Docker — can check container status (`docker ps`), restart a container
  (`docker restart uicp`), and read container logs (`docker logs uicp`).
  Does not need to build Docker images or write Dockerfiles.
- REST APIs — can use `curl` to test endpoints, read JSON responses, and
  identify error codes. Understands HTTP status codes (200, 400, 401,
  500, 503).
- Git — can clone a repository (`git clone`), pull the latest changes
  (`git pull`), and browse files on GitHub.
- Strong written communication — most support is email‑based. Must write
  clear, complete, professional responses to clients.
- Attention to detail — support issues often come down to a single
  character wrong in a regex pattern or a missing comma in a JSON file.
  Must be able to spot these errors.

**Nice to have (can learn on the job):**
- Basic understanding of regular expressions (regex).
- Basic understanding of JSON and YAML.
- Familiarity with any monitoring tool (Grafana, Prometheus, Datadog, or
  even a cron job that runs `curl`).

### How to Find This Person

Recent computer science or IT graduate from Makerere University, Kyambogo
University, or MUBS. Train them for two weeks on UICP specifically — the
first week is reading the System Bible and running the demo; the second
week is shadowing the founder on real support tickets.

This is an entry‑level role that grows with the company. The Support
Engineer who starts on Pilot tier clients will, within 12 months, have
the experience to handle Enterprise tier clients or move into a DevOps
role.

### Salary Range

**UGX 3,000,000–5,000,000 per month.**

---

## 2. UICP DEVOPS ENGINEER

**When to hire:** Five paying clients, or when the first Enterprise
client signs.

### What They Do Day‑to‑Day

- Deploy and manage UICP Docker containers across client environments.
  This includes on‑premises Linux servers, cloud VMs (AWS EC2, GCP
  Compute Engine, Azure VMs), and the UICP managed endpoint.
- Set up monitoring for every deployed instance: health check alerts
  (PagerDuty, Slack, or email), log aggregation (ELK stack, Loki, or
  CloudWatch), and performance dashboards (Grafana or Datadog).
- Manage PostgreSQL databases: daily backups, hourly incremental backups,
  replication setup, failover testing, and restoration drills.
- Run the monthly audit log archival job: identify partitions older than
  90 days, export to compressed JSON, upload to S3 or equivalent object
  storage, verify checksums, and drop the partitions from the live
  database.
- Automate constraint set deployment and rollback — when a client updates
  their constraints, the DevOps Engineer ensures the new constraint file
  is deployed to the correct container, the container is restarted (or
  the ConstraintStore hot‑reloads), and the health check confirms the
  deployment succeeded.
- Maintain the CI/CD pipeline for UICP engine updates. When a new engine
  version is released, the DevOps Engineer builds the Docker image, runs
  the full test suite against it, deploys it to staging, and then
  promotes it to production.
- Manage signing key infrastructure: generate new keys, store them
  securely (encrypted file for staging, HSM or KMS for production),
  rotate keys on schedule, and execute emergency revocation when needed.
- Conduct quarterly disaster recovery tests: simulate complete server
  failure, restore from backups, and verify that the recovery time
  objective (4 hours) and recovery point objective (1 hour) are met.

### Minimum Skills and Experience

**Must have:**
- Docker and container orchestration — strong, hands‑on experience.
  Can write Dockerfiles, manage multi‑container setups, and debug
  container networking issues. Experience with Docker Compose or
  Kubernetes is required.
- Linux system administration — strong. Can manage users, permissions,
  networking, firewalls, and systemd services on Ubuntu or Debian.
- Cloud platforms — at least one of AWS, GCP, or Azure. Can provision
  a VM, configure security groups, set up S3 buckets, and manage IAM
  roles.
- PostgreSQL administration — can perform backups (`pg_dump`,
  `pg_basebackup`), restores, replication setup, and basic performance
  tuning.
- Monitoring tools — experience with at least one of Prometheus,
  Grafana, Datadog, Nagios, or equivalent.
- Shell scripting and Python — intermediate. Can write scripts to
  automate routine tasks.
- Information security fundamentals — understands encryption at rest
  (AES), encryption in transit (TLS), key management, and access
  control principles.

**Nice to have:**
- Experience with CI/CD pipelines (GitHub Actions, Jenkins, or GitLab CI).
- Experience with infrastructure‑as‑code (Terraform, CloudFormation,
  or Ansible).
- Familiarity with compliance frameworks (SOC 2, ISO 27001, GDPR).

### How to Find This Person

Mid‑career DevOps engineer currently working at a Ugandan fintech,
telecommunications provider, or cloud services company. Look for someone
with 3–5 years of experience who wants to work on AI infrastructure
rather than traditional web applications.

### Salary Range

**UGX 5,000,000–8,000,000 per month.**

---

## 3. COMPLIANCE AND GOVERNANCE OFFICER

**When to hire:** Before SOC 2 Type II engagement begins (requires
production audit logs from a paying client).

### What They Do Day‑to‑Day

- Own the SOC 2 Type II audit process from start to finish: prepare
  evidence collection templates, liaise with the external audit firm,
  schedule and conduct quarterly control tests (access control in Month 3,
  change management in Month 5, disaster recovery in Month 7), and
  compile the final evidence package for the auditor.
- Maintain the Regulatory Change Register: monitor regulatory sources
  (EU AI Act amendments, NIST AI RMF updates, GDPR guidance, Uganda Data
  Protection and Privacy Act, sectoral regulations for each client),
  record every change that could affect UICP constraint sets, assign
  priority (CRITICAL if effective within 30 days), and track remediation
  through to constraint update and deployment.
- Review constraint sets for fairness and regulatory compliance before
  they are deployed to production. This is not a technical review — it
  is a governance review. The Compliance Officer asks: "Does this
  constraint set comply with applicable regulations? Could it produce
  discriminatory outcomes? Is it aligned with the client's stated
  governance policies?"
- Conduct monthly access control reviews: reconcile the list of users
  with admin access against the approved personnel list, verify that MFA
  is enabled for all admins, document the review, and flag any
  discrepancies.
- Maintain the AI Asset Register: ensure every AI model governed by
  UICP has a corresponding register entry with model version, constraint
  set version, extraction schema version, risk classification, and last
  review date. Follow up with clients whose register entries are
  overdue for review.
- Prepare quarterly NIST AI RMF compliance assessments using the UICP
  assessment framework, document the scores across all four functions
  (GOVERN, MAP, MEASURE, MANAGE), and track improvement over time.
- Manage data subject requests under GDPR: receive requests from clients,
  verify the data subject's identity, execute erasure or access requests
  within the statutory timeline, and document every action in the
  deletion audit trail.

### Minimum Skills and Experience

**Must have:**
- Regulatory compliance — understands at least two of the following
  frameworks in depth: GDPR, NIST AI RMF, SOC 2, ISO 27001, ISO 42001.
  Can read a regulation and translate it into operational requirements.
- Audit management — has participated in at least one external audit
  (SOC 2, ISO, or regulatory). Knows what evidence looks like, how to
  present it, and how to communicate with auditors.
- Policy drafting — can write clear, actionable policies and procedures
  that satisfy regulatory requirements without being unnecessarily
  complex.
- Strong written communication — regulatory submissions, client
  notifications, and audit responses must be precise and defensible.
- Attention to detail — compliance is about what you can prove, not
  what you believe. One missing evidence item can delay an audit by
  months.

**Nice to have:**
- Experience in financial services or healthcare compliance.
- Familiarity with African data protection regulations (Uganda Data
  Protection and Privacy Act, Kenya Data Protection Act, South Africa
  POPIA).
- Certified Information Privacy Professional (CIPP) or equivalent.

### How to Find This Person

Compliance officer or risk manager currently working at a Ugandan bank,
insurance company, or telecommunications provider. These industries have
mature compliance functions. The person already understands regulated
environments. Train them on AI‑specific frameworks (NIST AI RMF, EU AI
Act) — this is new to everyone, so domain expertise in compliance
processes matters more than AI‑specific knowledge.

### Salary Range

**UGX 4,000,000–7,000,000 per month.**

---

## 4. BUSINESS DEVELOPMENT LEAD

**When to hire:** After public launch — when the repository is public,
the demo video is live, and the documentation is complete.

### What They Do Day‑to‑Day

- Identify and qualify potential pilot partners in lending, healthcare,
  and government. This means researching companies, finding the right
  contact person (CTO, Head of Risk, Compliance Officer), and sending
  personalised outreach — not mass emails.
- Manage the pilot pipeline from first contact to signed agreement:
  send the one‑pager, schedule the kickoff call, demonstrate the live
  demo, answer technical questions (with support from the founder or
  Support Engineer), negotiate pilot terms using the standard Pilot
  Agreement template, and close.
- Prepare and deliver proposals for paid tiers when pilots convert.
  The proposal answers: "What did the pilot prove? What does the paid
  tier include? What is the ROI?"
- Represent UICP at industry events, conferences, and regulatory
  meetings in Kampala and, eventually, Nairobi, Kigali, and beyond.
- Manage relationships with existing clients: monthly check‑in calls,
  quarterly business reviews, renewal negotiations, and expansion (from
  Standard to Enterprise, from one constraint set to many).
- Track competitor activity and market trends in AI governance — what
  are other companies building? What are regulators saying? What are
  clients asking for that UICP does not yet do?
- Maintain the CRM (even if it starts as a Google Sheet): contact name,
  organisation, stage in pipeline, last contact date, next action,
  expected close date.

### Minimum Skills and Experience

**Must have:**
- Enterprise sales or business development — 3–5 years of experience
  selling a technical product to organisations with a procurement
  process. Must understand how to navigate multiple stakeholders (the
  champion, the economic buyer, the technical evaluator, the blocker).
- Understanding of at least one of these sectors: financial services,
  healthcare, or government procurement. Must speak the language of
  that sector — know the regulations, the pain points, and the buying
  cycle.
- Strong presentation and communication skills — can deliver a demo,
  answer questions on the spot, and adapt the message to the audience
  (CTO vs compliance officer vs CFO).
- Proposal writing and contract negotiation — can take a standard
  template and customise it for a specific client without introducing
  legal risk.
- Network in Kampala's business, technology, or government community —
  already knows people who can become clients or refer clients.

**Nice to have:**
- Experience selling to banks, insurance companies, or government
  agencies specifically.
- Understanding of AI and machine learning concepts (can explain what
  a constraint is and why deterministic enforcement matters).

### How to Find This Person

Business development manager currently selling enterprise software,
fintech solutions, or compliance services in Uganda. They already know
the buyers. They just need to learn the product.

### Salary Range

**UGX 4,000,000–8,000,000 per month, plus commission** of 5–10% on
first‑year contract value for signed deals.

---

## 5. TECHNICAL WRITER

**When to hire:** Three paying clients — when the volume of
documentation requests, client onboarding, and knowledge base
maintenance exceeds what the founder can handle alone.

### What They Do Day‑to‑Day

- Maintain the UICP System Bible (all nine parts): update it with
  every new feature, every new client requirement, and every new
  regulatory mapping. The System Bible is the single source of truth
  for UICP — it must never be out of date.
- Write and update client‑facing documentation: onboarding guides for
  new industries, API reference updates when new endpoints are added,
  troubleshooting guides when new failure modes are discovered, and
  FAQ entries when the same question is asked three times.
- Maintain the public knowledge base (`docs/KNOWLEDGE_BASE.md`) — ensure
  every article is findable, accurate, and written in plain English.
- Write case studies from pilot and production deployments: what was
  the problem, how was UICP configured, what were the results, what
  did the client say? Case studies are the single most powerful sales
  tool UICP has.
- Prepare grant reports and technical progress updates for funding
  agencies. Grant reports must be precise, evidence‑backed, and
  submitted on time.
- Write the UICP White Paper for academic publication and keep it
  updated as the system evolves.
- Ensure that every document in the repository follows a consistent
  style: same voice, same formatting, same quality. If a client reads
  the onboarding checklist and the API reference back‑to‑back, they
  should feel like the same person wrote both.

### Minimum Skills and Experience

**Must have:**
- Technical writing — 2–3 years of experience writing documentation
  that explains complex technical systems to non‑technical audiences.
  Must provide a portfolio of previous work (user manuals, API
  documentation, knowledge base articles, or similar).
- Markdown and Git — proficient. All UICP documentation is written in
  Markdown and stored in the GitHub repository. Must be comfortable
  creating files, editing them, and submitting pull requests.
- Python — basic. Must be able to read Python code, understand what
  an API endpoint does, and test it using `curl` or a Python script.
  Does not need to write production code.
- Strong research skills — can take a technical conversation with the
  founder or an engineer and turn it into clear documentation without
  losing accuracy.
- Attention to detail — a typo in a constraint example or a wrong
  field name in an API reference wastes hours of client time.

**Nice to have:**
- Experience writing about AI, machine learning, or cybersecurity.
- Experience with static site generators (MkDocs, Docusaurus, or
  similar).
- Familiarity with OpenAPI/Swagger specifications.

### How to Find This Person

Technical writer currently working at a Ugandan technology company,
telecommunications provider, or international NGO with a Kampala
office. Look for someone who has written user manuals, API
documentation, or training materials. Ask for their portfolio — a
good technical writer can show you documentation that made a complex
product easy to use.

### Salary Range

**UGX 3,000,000–5,000,000 per month.**

---

## 6. FOUNDER / CHIEF ENGINEER (Emmanuel Semugga)

**Role until first hires are made:** Everything — engineering,
support, business development, compliance, documentation.

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
HOW HIRE IN UGANDA

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
   immediately. 
