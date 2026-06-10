FROM: Emmanuel Semugga / UICP
TO: Audit Firm
DATE: 10 June 2026
SUBJECT: SOC 2 Type II Audit RFP

SYSTEM DESCRIPTION:
UICP (Universal Integrity Constraint Protocol) is a deterministic constraint
enforcement gateway deployed on AWS with Docker Compose, PostgreSQL, nginx,
and multi-tenant isolation. The system enforces lending constraints
(age, credit score, income) for financial institutions.

ARCHITECTURE IN SCOPE:
- API Layer: Python Flask/FastAPI with Ed25519 authentication
- Data Layer: PostgreSQL (audit logs, constraint versions, tenant data)
- Infrastructure: Docker Compose with nginx load balancing
- Monitoring: Performance profiler (GAP-48), alerts (GAP-50)
- Audit: Append-only signed audit log (Ed25519 signatures)
- Compliance: GDPR personal data store with encryption (AES-256)

TRUST SERVICE CRITERIA TO CERTIFY (CC, A, I):
CC (Common Criteria): Logical access control, system monitoring
A (Availability): Uptime ≥99.9%, redundancy, failover
I (Integrity): Audit logging, version control, change management

OBSERVATION PERIOD: 6 months (Month 1-8, 2026)
REPORT DELIVERY: Month 8-9

QUESTIONS FOR AUDITOR:
1. How many SOC 2 Type II audits have you completed? (Need 20+ minimum)
2. Do you have financial services experience (banking, payments)?
3. Can you commit to Month 8 report delivery with fixed pricing?
4. What's your ISO 42001 capability (we may add later)?
5. References: 2 financial services clients who did SOC 2 with you?

BUDGET RANGE: $50-100K fixed price (all-inclusive, no additional hours)
TIMELINE: Start Month 1, kickoff meeting Week 1 of Month 1

CONTACT:
Name: Emmanuel Semugga
Email: emmanuelsemugga@gmail.com
Phone: +256 704 233 469
Availability: Monday-Friday 9 AM - 5 PM EAT (UTC+3)
