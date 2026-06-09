# UICP Independent Verification Guide

## Version 1.0 — Final
### Audience: Regulators, Auditors, Grant Committees, Security Researchers, Prospective Clients

---

## WHAT THIS GUIDE ENABLES

This guide enables any independent party to verify every cryptographic claim made by a UICP deployment — without accessing the UICP source code, without contacting the UICP development team, and without trusting any statement made by the deploying organisation.

Using a single Python script and a standard cryptographic library, an auditor can confirm that an exported audit bundle is authentic, complete, and was produced by the legitimate UICP enforcement gateway. Every Ed25519 signature is verified. Every cryptographic chain link is validated. Every proof is checked.

This verification is not based on trust. It is based on mathematics.

## WHAT THIS GUIDE DOES NOT ENABLE

This verification does not and cannot validate whether the deploying organisation's constraints were correctly defined, whether the extracted binding values reflect reality, or whether the enforcement engine's internal logic is correct. Those questions require access to the UICP internal engines, which are available under controlled disclosure to paying clients and their designated auditors.

This verification also cannot validate whether a specific ALLOW or BLOCK decision was the correct decision — only that it was the decision produced by the legitimate gateway under the constraint set in force at that time.

## WHAT YOU NEED

To run the verification, you need four things.

First, an exported audit bundle from the UICP deployment you wish to verify. The deploying organisation must provide this to you. The bundle is a directory containing five files: `phase4_chain.json` (the complete enforcement decision log), `phase5_chain.json` (the cryptographic proof chain), `constraint_commitment.json` (the signed constraint set commitment), `manifest.json` (the integrity manifest), and `public_keys.json` (the gateway and operator public keys).

Second, the `verify_uicp_bundle.py` script. This script is available in the UICP public repository at `github.com/emmanuelsemugga-code/uicp-pipeline`. It is a standalone Python file with no dependencies on any UICP internal module.

Third, Python 3.12 or later installed on your machine.

Fourth, the `cryptography` Python package, which you can install with `pip install cryptography`. This is a widely audited, open‑source cryptographic library used by thousands of organisations. UICP contains no custom cryptographic code.

## HOW TO RUN THE VERIFICATION

After you have the audit bundle directory and the verification script, run a single command.

From your terminal:
