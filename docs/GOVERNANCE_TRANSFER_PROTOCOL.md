# UICP Governance Transfer Protocol

## Version 1.0 — Final
### Status: Active
### Audience: CTOs, General Counsel, Compliance Officers, M&A Teams, Regulators

---

## THE SCENARIO NO ONE PLANS FOR

A regulated financial institution deploys UICP to enforce constraints on its AI‑driven lending decisions. The constraint set is mature, validated, and signed by two independent operators. The audit log contains three years of cryptographically signed enforcement records. The encryption keys are securely stored. The extraction schemas are tuned to the institution's specific AI models. The AI Asset Register is current.

Then the institution is acquired. The acquiring entity has its own AI systems, its own governance framework, its own compliance team, and its own interpretation of the same regulations. It may operate in different jurisdictions with different legal requirements. It may use different AI models with different output formats.

What happens to UICP?

This is not a hypothetical scenario. Mergers and acquisitions in regulated industries occur daily. In 2025 alone, over two hundred financial institutions in the European Union were involved in M&A activity. Every one of them had AI systems. None of them had a protocol for transferring AI governance to the acquirer.

The consequences of an unplanned transfer are severe. The constraint set may be incompatible with the acquirer's AI models. The audit log may be in a format the acquirer cannot verify. The encryption keys may be held by individuals who are no longer with the organisation. The regulatory commitments made by the acquired entity may be unknown to the acquirer. The AI Asset Register may be incomplete or outdated.

If UICP is simply decommissioned during the acquisition, the enforcement gap that UICP was designed to close reopens immediately. Decisions that were previously checked against formal constraints are now unchecked. The audit trail ends. The cryptographic proofs stop. The regulator, reviewing the acquisition, will ask: "What happened to the governance controls that were in place?"

This protocol exists to ensure that the answer is never "We don't know."

## THE TRANSFER PRINCIPLE

UICP governance is transferable by design. The constraint sets are portable JSON documents. The audit logs are standardised, verifiable, and exportable. The encryption keys are managed with documented key lifecycle procedures. The extraction schemas are version‑controlled. The AI Asset Register is a structured document.

Every component of UICP governance can be handed from one organisation to another without loss of integrity, without loss of auditability, and without creating an enforcement gap. But the handover must follow a defined protocol. An unplanned, ad‑hoc transfer will create gaps. A protocol‑driven transfer will not.

## THE TRANSFER CHECKLIST

The transfer of UICP governance from the transferring entity to the receiving entity follows a five‑stage checklist. Every stage must be completed. Every stage produces auditable records. No stage may be skipped.

### Stage 1 — Inventory and Verification

The transferring entity must produce a complete inventory of all UICP assets. This inventory must include every constraint set currently active, every constraint set version in the version history, every extraction schema currently in use, every extraction schema version in the version history, every active signing key, every revoked or rotated signing key, the complete AI Asset Register, the complete audit log, the complete Regulatory Change Register, the complete governance records for every model version change, and the complete incident response records.

The receiving entity must verify the integrity of these assets before accepting them. The audit log must be verified using the public verification scripts — the cryptographic chain must be intact, every Ed25519 signature must be valid, and the manifest export IDs must match. The constraint sets must be run through the Constraint Validator, the Dependency Analyzer, and the Consistency Checker. Any errors discovered during verification must be resolved before the transfer proceeds.

### Stage 2 — Key Transfer

The signing keys are the most sensitive asset in the transfer. They must be transferred through a secure channel — encrypted transport, separate from the data transfer, with access limited to authorised individuals on both sides.

The receiving entity must generate new signing keys for future operations. The transferred keys are retained for historical signature verification only. The receiving entity must never use the transferred keys to sign new decisions. This ensures that if the transferred keys were compromised during the transfer, future decisions are not affected.

The receiving entity must register its new signing keys in the operator registry. The receiving entity's compliance officer must sign a new constraint commitment using the new keys, establishing the chain of governance continuity.

### Stage 3 — Constraint Migration

The constraint sets must be mapped to the receiving entity's AI models. This mapping is not automatic. The receiving entity's AI models may use different variable names, different output formats, or different value ranges. The extraction schemas must be updated accordingly.

Each constraint set must be reviewed by the receiving entity's constraint owner. The review must confirm that the constraints are still appropriate for the receiving entity's risk appetite, that the thresholds are still compliant with the receiving entity's regulatory obligations, and that the extraction schemas correctly parse the receiving entity's model outputs.

If the receiving entity operates in different jurisdictions than the transferring entity, the constraint sets must be reviewed for jurisdiction‑specific compliance. A constraint that is compliant in Ireland may not be compliant in the United States. A constraint that satisfies the EU AI Act may not satisfy sectoral regulations in the receiving entity's industry.

### Stage 4 — Audit Log Transfer

The complete audit log — every signed enforcement decision, every commitment, every proof, every override — must be transferred. The audit log must remain verifiable after transfer. The receiving entity must be able to verify the cryptographic chain using only the public keys and the exported manifest.

The audit log must be retained for the regulatory retention period of the most stringent applicable jurisdiction. If the transferring entity was subject to a seven‑year retention requirement and the receiving entity is subject to a ten‑year requirement, the log must be retained for ten years.

The receiving entity must not merge the transferred audit log with its own audit log. The two logs must be maintained as separate, independently verifiable chains. The transfer creates a new governance origin for the receiving entity's future decisions, but it does not erase the governance history of the transferring entity.

### Stage 5 — Regulatory Notification

The transfer of UICP governance may constitute a material change in the governance of AI systems that must be notified to regulators. The receiving entity's compliance officer must assess whether notification is required under applicable regulations.

If the AI systems governed by the transferred constraints are classified as high‑risk under the EU AI Act, the transfer must be notified to the relevant notified body. If the transfer changes the entity responsible for GDPR compliance, the relevant data protection authority must be notified. If the transfer affects systems subject to sectoral regulation, the relevant sectoral regulator must be notified.

The notification must include the date of transfer, the identity of the transferring and receiving entities, the constraint sets transferred, the AI models affected, and confirmation that the transfer was completed in accordance with this protocol.

## POST‑TRANSFER VERIFICATION

Within thirty days of the transfer, the receiving entity must complete a post‑transfer verification. This verification confirms that the constraint sets are being correctly enforced on the receiving entity's AI models, that the audit log is being correctly written to the receiving entity's audit database, that the new signing keys are correctly registered and used for all new decisions, that the AI Asset Register has been updated to reflect the transferred assets, and that all regulatory notifications have been completed.

The post‑transfer verification must be documented and retained with the transfer records.

## WHAT HAPPENS IF THE TRANSFERRING ENTITY IS INSOLVENT OR UNAVAILABLE

If the transferring entity is insolvent, dissolved, or otherwise unavailable to participate in the transfer, the receiving entity must proceed with the assets that are available. This is not an ideal scenario, but it is a realistic one.

If the constraint sets are available — they are stored in version control or in the ConstraintStore database — they can be migrated without the transferring entity's cooperation. If the audit log is available, it can be verified and retained. If the signing keys are available, they can be transferred for historical verification.

If the signing keys are not available, the receiving entity cannot verify historical signatures. This is a permanent gap in the audit trail. It must be documented and disclosed to regulators. The receiving entity must generate new signing keys for future operations and note in the governance record that historical decisions signed by the transferring entity's keys are not verifiable.

This scenario is why the transferring entity should maintain secure, accessible key storage. The Key Lifecycle Manager supports encrypted key export specifically for transfer scenarios.

## THE MARKET REALITY

In June 2026, no AI governance framework provides a protocol for transferring governance controls during an acquisition. This is not because transfers are rare. It is because most AI governance is not infrastructure — it is documentation. Policies are transferred as PDFs. Training materials are transferred as slide decks. Model documentation is transferred as spreadsheets.

None of these transfers preserves the operational integrity of the governance controls. The policies may be read by the acquirer's compliance team or they may not. The training materials may be integrated or discarded. The model documentation may be accurate or it may be two versions out of date.

UICP is different because UICP is infrastructure. The constraint sets are not documents — they are executable rules that control whether decisions are allowed or blocked. The audit log is not a report — it is a cryptographically signed, verifiable record of every enforcement decision. The governance records are not summaries — they are complete histories of every constraint change, every validation, every simulation, every deployment.

When UICP governance is transferred, it must be transferred with the same rigour as any other critical infrastructure. This protocol defines that rigour.

## THE PROOF THAT THE TRANSFER WAS CORRECT

After the transfer is complete, the receiving entity's auditor must be able to answer the following questions with cryptographic certainty.

Question: Were the constraint sets correctly transferred?
Answer: Yes. The receiving entity ran the Constraint Validator, Dependency Analyzer, and Consistency Checker against every transferred constraint set. All passed. The receiving entity ran the Simulation Engine against historical decisions and confirmed that the constraint sets produce the expected results.

Question: Is the audit log intact and verifiable?
Answer: Yes. The receiving entity verified the complete cryptographic chain using the public verification scripts. Every Ed25519 signature is valid. The manifest export IDs match.

Question: Are the signing keys secure?
Answer: The transferred keys are stored for historical verification only. The receiving entity generated new keys for all future operations. The new keys are registered in the operator registry.

Question: Were regulators notified?
Answer: Yes. Notifications were sent to all applicable regulatory bodies within the required timeframe. Copies of the notifications are retained in the governance record.

Question: Is UICP enforcing constraints correctly on the receiving entity's AI models?
Answer: Yes. The post‑transfer verification confirmed that enforcement is operational, the audit log is being written correctly, and the new signing keys are being used for all decisions.

These answers are not based on trust. They are based on cryptographic proof, documented procedures, and auditable records. This is what makes UICP governance transferable in a way that no other AI governance framework is.

## REVIEW CADENCE

This protocol must be reviewed annually. It must also be reviewed after every governance transfer — the lessons learned from each transfer must be incorporated into the next version of this protocol.

The next scheduled review is June 2027.

---

**END OF GOVERNANCE TRANSFER PROTOCOL**
