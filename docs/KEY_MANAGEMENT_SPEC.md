# UICP Key Management Specification

## Version: 1.0.0
## Date: May 2026
## Status: Active
## Implements: GAP-13 (Key Rotation/Revocation) + GAP-14 (HSM/Storage)

---

## Key Types

| Key Type | Used For | Managed By |
|---|---|---|
| Operator key | Constraint set signing, commitment | KeyLifecycleManager |
| Gateway key | Decision record signing (Phase 4) | Phase4EnforcementGateway |
| Audit key | Phase 5 proof signing | Phase5Engine |

---

## Key Validity Periods

| Environment | Default Validity | Maximum Validity |
|---|---|---|
| Development | Session only | Session only |
| Staging | 12 months | 24 months |
| Production | 12 months | 12 months |

Keys must be rotated before expiry. Expired keys cannot sign.
Expired keys can verify historical signatures.

---

## Storage Requirements By Environment

### Development
- IN-MEMORY ONLY
- Fresh key pair generated each session
- Never write private keys to disk in development
- Acceptable for testing and local development only

### Staging
- AES-256-GCM encrypted file
- Encryption key stored in environment variable KEY_ENCRYPTION_KEY
- File path: /secrets/operator_key.enc
- File must not be in the same directory as audit chain files
- Backup encrypted file separately from encryption key

### Production — MANDATORY
- Hardware Security Module (HSM) or equivalent KMS
- Private key never leaves the HSM boundary
- Sign operations performed inside HSM
- Acceptable implementations:
  - AWS KMS with CloudHSM
  - Azure Key Vault with HSM backing
  - Google Cloud KMS with HSM protection level
  - HashiCorp Vault with HSM backend
  - On-premises FIPS 140-2 Level 3 HSM
- NEVER store production private keys in files or environment variables

---

## Key Rotation Procedure

1. Generate new key via KeyLifecycleManager.generate_key()
2. Register new public key with OperatorRegistry
3. Call KeyLifecycleManager.rotate(old_key_id, ...) — old key → ROTATED
4. Update all consuming systems with new key_id
5. Verify historical signatures still verifiable under old key_id
6. Record rotation event in audit log
7. Retain old public key in registry — required for historical verification

Rotation must occur:
- Before key expiry (12 months default)
- Immediately on suspected compromise (use revoke() instead)
- When operator leaves the organization

---

## Key Revocation Procedure

**Use when:** Key is confirmed or suspected compromised.

1. Call KeyLifecycleManager.revoke(key_id, reason) immediately
2. reason must be specific — "Suspected compromise — key exposed in CI logs"
3. Generate replacement key immediately
4. Notify all verifiers that key_id is revoked
5. Audit all decisions signed under revoked key_id
6. Document incident in RESIDUAL_RISK_REGISTER.md

**Effect of revocation:**
- ALL signatures from revoked key are rejected
- Historical signatures are NOT preserved (unlike rotation)
- This is the critical distinction between rotation and revocation

---

## Prototype Exception

Current deployment generates keys in-memory each session.
This is acceptable for development and testing only.

Before first regulated client:
- Staging: implement encrypted file storage
- Production: implement HSM integration
- Document key_id values in audit bundle public_keys.json

---

## Review Cadence

Quarterly or on any of:
- Key compromise or suspected compromise
- Operator departure
- New deployment environment
- Regulatory requirement change

**Next review due:** August 2026
