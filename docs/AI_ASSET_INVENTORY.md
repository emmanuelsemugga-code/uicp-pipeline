# UICP AI Asset Inventory Protocol

## Version 1.0 — Final
### Status: Active
### Audience: CTOs, AI Governance Leads, Compliance Officers, Auditors, Regulators

---

## THE PROBLEM NO ONE IS TALKING ABOUT

Every major AI governance framework — the EU AI Act, the NIST AI Risk Management Framework, ISO/IEC 42001, the AICPA AI Control Framework — requires organisations to maintain an inventory of their AI systems. This is not a recommendation. It is a legal obligation.

The EU AI Act, Article 11, requires that high‑risk AI systems be accompanied by technical documentation describing the system's design, purpose, and behaviour. The NIST AI RMF, Map function, requires organisations to establish the context of every AI system they operate. GDPR, Article 30, requires records of processing activities for any system that handles personal data.

Every regulated organisation on the planet must answer the question: "What AI systems do you have, where are they, what do they do, and how do you govern them?"

Today, in June 2026, the answer to that question is almost always a spreadsheet. A manually maintained Excel file or Google Sheet that is out of date the moment it is completed. No major AI governance platform — not IBM Watson OpenScale, not Hugging Face SafetyKit, not Anthropic's Responsible Scaling Policy, not any of the emerging AI registry startups — connects the inventory of AI models to a deterministic constraint enforcement layer.

What this means in practice is that an organisation can show a regulator a list of its AI systems. It can show the regulator a set of policies. It can show the regulator a set of constraints. But it cannot show the regulator proof that those constraints were actually enforced on those AI systems at the moment of decision. The spreadsheet does not connect to the enforcement gateway. The policy document does not connect to the audit log. The constraint set does not connect to the model version.

This gap — the missing connection between "what we say we govern" and "what we actually enforce" — is the single largest unaddressed risk in enterprise AI governance.

## WHAT UICP DEMANDS THAT NO OTHER SYSTEM DEMANDS

UICP closes this gap with a simple, non‑negotiable requirement: every AI model in production must have a corresponding entry in the AI Asset Register, and every entry in the register must reference a specific, versioned constraint set and a specific, versioned extraction schema.

This is not a recommendation. It is the admission criterion for UICP enforcement. If a model is not in the register, it has no constraint set. If it has no constraint set, UICP cannot enforce anything on its outputs. The enforcement gateway will reject enforcement requests for any model that is not registered.

This requirement forces the organisation to do what no current governance framework forces it to do: maintain a live, accurate, verifiable connection between the inventory of AI systems and the enforcement of constraints on those systems.

The consequence of failing to maintain this connection is immediate and operational — not just a compliance finding six months later. If a model is updated without updating its register entry, the extraction schema may break, the constraint set may become incompatible, and enforcement decisions will fail. The system fails safe — it blocks decisions rather than allowing them to pass unenforced — but the operational disruption forces the governance process to stay current.

This is fundamentally different from every existing AI governance tool. Existing tools alert you that something might be wrong. UICP refuses to operate until it is right.

## THE AI ASSET REGISTER

The AI Asset Register is a structured document maintained by the organisation's AI governance lead. It can be a JSON file, a database table, or a governance platform entry. Its format matters less than its completeness and its connection to the enforcement layer.

Every entry in the register must contain at minimum the following information.

The asset ID is a unique identifier that links this register entry to the constraint set and extraction schema in UICP. The model name and version identify exactly what is deployed. The model type — classification, regression, large language model, or other — determines the applicable regulatory framework. The provider identifies who built or maintains the model.

The deployment date records when this version entered production. This date is critical for audit purposes: if a decision is later challenged, the deployment date establishes whether the constraint set was active at the time of the decision.

The purpose field describes what business function the model serves. This is not a technical description — it is a governance description. It answers the regulator's question: "What is this system used for?" The input data field describes what data the model consumes. The output format field describes how the model returns results. Together, these three fields provide the context that the NIST AI RMF Map function requires.

The UICP constraint set field is the critical connection. It specifies exactly which constraint set version governs this model. This is not a policy reference. It is a technical reference to a specific, versioned, cryptographically signed constraint set in the UICP system. If this field is wrong, enforcement is wrong.

The UICP extraction schema field specifies which schema is used to extract bindings from this model's output. If the model's output format changes and the schema is not updated, extraction will fail and enforcement will block decisions.

The risk classification field records the model's classification under the EU AI Act or equivalent framework. The review cadence and last reviewed date establish the governance rhythm.

The status field — ACTIVE, DEPRECATED, or RETIRED — defines the model's lifecycle position.

## ASSET LIFECYCLE

Every AI asset in the register follows a defined lifecycle with four stages.

Registration occurs when a new AI model is deployed to production and will be subject to UICP enforcement. The model owner completes the register entry. The constraint owner verifies that a constraint set exists and is registered in UICP for this model. The extraction schema is tested against sample model outputs to confirm correct binding extraction. The compliance officer approves the registration. Only after all four steps are complete does UICP begin enforcing constraints on this model's outputs.

Review occurs at the defined cadence — default quarterly. The review confirms that the model version in the register matches the deployed version, that the constraint set is still appropriate for the model's current behaviour, that the extraction schema still correctly parses the model's output format, and that the risk classification is still accurate under current regulations. Review results are recorded in the register.

Deprecation occurs when a model version is being replaced. The model owner marks the current version as DEPRECATED. The new model version is registered. The constraint set for the deprecated version is deactivated. The deprecated entry is retained for audit purposes.

Retirement occurs when a model is permanently decommissioned. The entry is marked RETIRED. The constraint set is deactivated. The audit log is archived according to the retention policy. The register entry is retained for the regulatory retention period — default seven years.

## THE CONNECTION THAT NO OTHER SYSTEM MAKES

The AI Asset Register is not a standalone governance document. It is the bridge between organisational governance and technical enforcement. Every entry must reference a specific constraint set version and a specific extraction schema version. This mapping is what enables a regulator to trace from a specific AI model to its constraint set to its enforcement decisions — and to verify, cryptographically, that those decisions were correctly enforced.

This connection is verified quarterly. The extraction schema is run against a sample of the model's current output to confirm correct extraction. The Constraint Validator, part of the UICP toolchain, is run against the constraint set to confirm it remains valid. The model version in the register is checked against the deployed version. The last_reviewed field is updated. Any discrepancy blocks enforcement until resolved.

## WHAT HAPPENS WHEN AN ORGANISATION FAILS TO MAINTAIN THIS CONNECTION

If a model is deployed without a register entry, UICP has no constraint set to enforce. Enforcement requests for that model will fail. The system will not guess. It will not default to ALLOW. It will return GATEWAY_UNAVAILABLE and require manual review. This is an operational failure that will be noticed immediately — not a compliance finding that will be discovered months later.

If a model is updated without updating the register, the extraction schema may become incompatible. Binding extraction will fail. Enforcement will fail. Again, the failure is immediate and operational.

If a constraint set is updated without updating the register, the register will reference an inactive version. The next quarterly review will detect the mismatch.

This design ensures that the register cannot become stale without operational consequences. The enforcement gateway demands accuracy. The organisation's governance process must supply it.

## COMPLIANCE ALIGNMENT

This protocol directly satisfies the technical documentation requirements of the EU AI Act Article 11. It provides the system context required by the NIST AI RMF Map function. It establishes the documented information controls required by ISO/IEC 42001 Clause 7.5. It supports the records of processing activities required by GDPR Article 30.

No existing AI governance platform provides this level of integration between asset inventory and constraint enforcement. The spreadsheet is replaced by a live, verifiable, cryptographically connected register that directly controls whether AI outputs are allowed or blocked.

## PROTOTYPE EXCEPTION

In the current pilot deployment, the AI Asset Register may be maintained as a simple JSON file. Before regulated production deployment, the register should be integrated with the organisation's existing IT asset management system or governance platform. The format may change. The requirement does not: every model must be registered, and every registration must connect to a constraint set.

## REVIEW CADENCE

This protocol must be reviewed annually. It must also be reviewed when a new AI model type is added to the organisation, or when a new regulatory framework requires additional inventory fields. The next scheduled review is June 2027.

---

**END OF AI ASSET INVENTORY PROTOCOL**
