# UICP Regulatory Content Governance Process

## Version 1.0 — Final
### Status: Active
### Audience: Compliance Officers, Legal Counsel, AI Governance Leads, Regulators

---

## THE PROBLEM THAT NO GOVERNANCE FRAMEWORK SOLVES

Regulations change. The EU AI Act will be amended. NIST AI RMF will release version 2.0. Sectoral regulators — the FDA, the FCA, the OCC, the ECB — will issue new guidance. A constraint set that was compliant in June 2026 may be insufficient in June 2028.

Every AI governance framework acknowledges this problem. The EU AI Act requires that high‑risk AI systems be subject to continuous monitoring and that their technical documentation be kept up to date. The NIST AI RMF Manage function requires that organisations respond to changing risks. ISO/IEC 42001 requires management review and continual improvement.

None of these frameworks, however, provides a mechanism for translating a regulatory change into an updated constraint set. None of them connects the abstract requirement of "keep your governance current" to the concrete requirement of "update the mathematical inequality that controls whether a loan is approved or a medication is prescribed."

This is the gap that UICP's Regulatory Content Governance Process closes. It defines exactly what must happen when a regulation changes: who is responsible, what steps are taken, what tools are used, what records are kept, and how the updated constraints are deployed to production without creating a compliance gap.

## THE REGULATORY CHANGE REGISTER

Every regulatory change that could affect an organisation's constraint sets must be recorded in the Regulatory Change Register. This register is not a passive log. It is an active governance tool that triggers constraint reviews, tracks remediation timelines, and provides auditable evidence to regulators that the organisation systematically maintains its compliance posture.

The register records the source of the change — the specific regulation, guidance document, or enforcement action that triggers the review. It records the date the change was published or became known to the organisation. It records the sections or articles that are relevant. It identifies which constraint sets may be affected. It assigns a priority: CRITICAL if the change takes effect within 30 days or imposes new mandatory requirements, HIGH if it takes effect within 90 days or materially alters existing requirements, STANDARD if it takes effect within 180 days and requires only minor adjustments.

The register records the review completion date, the actions taken — constraints updated, constraints added, constraints removed — and the new constraint set version that incorporates the change. It records the name of the reviewer and the name of the approver. Every entry is retained for the regulatory retention period.

A quarterly review of the Regulatory Change Register is mandatory. If any CRITICAL or HIGH priority change has not been addressed within its timeline, enforcement is not affected — but the compliance officer must report the gap to the organisation's risk committee and document the reason for the delay.

## SOURCES OF REGULATORY CHANGE

The organisation must identify and monitor the regulatory sources that could affect its constraint sets. These sources vary by industry and jurisdiction, but a minimum set is required.

Primary legislation in the organisation's operating jurisdictions must be monitored. This includes the EU AI Act for organisations operating in the European Union, the proposed UK AI Bill for the United Kingdom, and any federal AI legislation enacted in the United States. Sectoral legislation must also be monitored: the Fair Credit Reporting Act and Equal Credit Opportunity Act for financial services, the Food, Drug, and Cosmetic Act for healthcare, and equivalent legislation in other jurisdictions.

Regulatory guidance and implementing rules must be monitored. The EU Commission publishes delegated acts and implementing acts under the AI Act. The FDA publishes guidance documents on AI in medical devices. The OCC, Federal Reserve, and CFPB publish interagency guidance on AI in financial services. Each of these documents can change the interpretation of a constraint without changing the underlying legislation.

Industry standards must be monitored. NIST publishes updates to the AI Risk Management Framework. ISO publishes revisions to ISO/IEC 42001 and ISO/IEC 27001. The AICPA updates its AI Control Framework. Changes to these standards do not have the force of law, but they establish the standard of care against which an organisation's governance will be measured in litigation or enforcement.

Enforcement actions and regulatory settlements must be monitored. When a regulator fines a peer organisation for a specific AI governance failure, that enforcement action effectively defines a new compliance requirement. If the UK Information Commissioner fines a lender for discriminatory AI decisions, every other lender's constraint set must be reviewed against the standard articulated in that enforcement action.

Case law must be monitored. Courts interpret legislation. A court ruling that clarifies the definition of "high‑risk AI system" or "automated decision‑making" can change the scope of constraints that must be enforced.

The organisation must designate a regulatory monitoring owner — a named individual responsible for tracking these sources and entering changes into the Regulatory Change Register. In a small organisation, this may be the compliance officer. In a large organisation, this may be a dedicated regulatory intelligence team. What matters is that the role is assigned, not that it is full‑time.

## FROM REGULATORY CHANGE TO CONSTRAINT UPDATE

When a regulatory change is entered into the register, it triggers a defined process that connects the abstract regulatory requirement to the concrete constraint set.

The first step is impact assessment. The constraint owner, in consultation with legal counsel if necessary, determines which constraint sets are affected. Not every regulatory change affects every constraint set. A change to lending regulations does not affect healthcare constraints. A change to the EU AI Act's transparency requirements may not affect any constraint directly — it may only require documentation updates.

The second step is constraint revision. For each affected constraint set, the constraint owner drafts updated constraints that reflect the new regulatory requirement. The updated constraints must be written in the canonical form that UICP enforces — as mathematical inequalities, not as policy language.

The third step is validation. The updated constraint set is run through the Constraint Validator to check for syntax errors, semantic errors, contradictions, and redundancy. It is run through the Dependency Analyzer to identify impact chains and circular dependencies. It is run through the Consistency Checker to detect unsatisfiable constraint combinations. All errors must be resolved before the updated constraint set can proceed.

The fourth step is simulation. The Simulation Engine replays historical decisions against the updated constraint set to measure the impact of the change. If the updated constraints would have changed the outcome of historical decisions — blocking loans that were previously allowed, or allowing treatments that were previously blocked — the simulation report quantifies that impact. The constraint owner and compliance officer must review the simulation and confirm that the impact is both expected and acceptable.

The fifth step is deployment. The updated constraint set is deployed using the Canary Deployment Manager, starting at one percent of traffic and progressively increasing to full deployment. The SLA Manager monitors latency and error rates throughout the deployment. If any anomaly is detected, the deployment is rolled back and the constraint set is revised.

The sixth step is documentation. The Regulatory Change Register entry is updated with the completion date, the actions taken, the new constraint set version, and the names of the reviewer and approver. The complete governance record — the regulatory change notice, the impact assessment, the validation reports, the simulation report, the canary deployment metrics — is archived for the regulatory retention period.

## ROLES AND RESPONSIBILITIES

The regulatory monitoring owner identifies and records regulatory changes. This person must have access to regulatory intelligence sources — subscriptions to legal databases, membership in industry associations, or relationships with external counsel.

The constraint owner assesses the impact of regulatory changes on specific constraint sets and drafts updated constraints. This person must understand both the regulatory requirement and the mathematical form that constraints take in UICP.

The compliance officer approves all constraint changes that are driven by regulatory requirements. This approval is a legal determination that the updated constraint set satisfies the regulatory obligation. It is not a technical determination.

The operator deploys the updated constraint set using the Canary Deployment Manager and monitors the deployment for anomalies.

In a single‑person deployment, one individual holds all four roles. This is documented as a prototype exception and must be resolved before regulated production deployment. At minimum, the compliance officer role must be separated from the constraint owner role.

## THE CONSEQUENCE OF FAILING TO MAINTAIN REGULATORY CONTENT

If a regulatory change is identified but the constraint set is not updated, UICP continues to enforce the old constraints. The enforcement gateway does not know that the regulation has changed. It faithfully enforces the constraints it was given.

This means that the organisation may be enforcing outdated rules. A loan may be approved under a threshold that is no longer legal. A medication may be recommended under a guideline that has been superseded. UICP will sign these decisions and record them in the audit log — providing cryptographic proof that the organisation enforced the wrong rules.

This is not a failure of UICP. It is a failure of the governance process that feeds UICP its constraints. UICP is a tool. The tool enforces what it is given. This governance process exists to ensure that what UICP is given is always current, always accurate, and always legally defensible.

The Regulatory Change Register is the organisation's evidence that it has a systematic process for maintaining regulatory content. The Constraint Staleness Detector flags any constraint that has not been reviewed within its defined window. Together, they provide the compliance officer with the tools to prevent regulatory drift.

## THE MARKET REALITY THAT THIS PROCESS ADDRESSES

In June 2026, most organisations that deploy AI systems do not have a systematic process for updating constraints in response to regulatory changes. They update their policies. They update their training materials. They may update their model documentation. But they do not update the mathematical rules that govern their AI decisions — because most organisations do not have mathematical rules governing their AI decisions. They have prompt engineering. They have guardrails. They have manual review. They do not have deterministic constraint enforcement.

For those organisations, a regulatory change triggers a policy review and a training update. The connection between the regulation and the decision is mediated by human judgment — which is fallible, inconsistent, and unauditable.

For an organisation using UICP, a regulatory change triggers a constraint update. The updated constraint is tested, simulated, deployed, and verified. The audit log records exactly which constraint version was in force at the time of every decision. The regulator can verify, cryptographically, that the correct constraint was enforced.

This is the difference between governance as documentation and governance as infrastructure. This process makes UICP the bridge between the two.

## REVIEW CADENCE

This governance process must be reviewed annually. It must also be reviewed when a new regulatory framework applicable to the organisation comes into force, or when the organisation expands into a new jurisdiction with different regulatory requirements.

The next scheduled review is June 2027.

---

**END OF REGULATORY CONTENT GOVERNANCE PROCESS**
