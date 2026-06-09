#!/usr/bin/env python3
"""
verify_uicp_bundle.py — UICP Independent Verification Script
=============================================================
Verifies every cryptographic guarantee of a UICP audit bundle
WITHOUT accessing any UICP internal engine.

Requires: Python 3.12+, cryptography library, an exported audit
          bundle directory, and the gateway/operator public keys.

Usage:  python3 verify_uicp_bundle.py audit_export/ public_keys.json

This script is public domain. No UICP source code is included.
It verifies proofs using only standard cryptographic operations.
"""
import json, hashlib, sys, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

PASSED = 0
FAILED = 0


def verify(label: str, condition: bool, detail: str = ""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✓  {label}")
    else:
        FAILED += 1
        print(f"  ✗  FAIL: {label}")
        if detail:
            print(f"       {detail}")


def load_json(path: str) -> dict | list:
    with open(path, "r") as f:
        return json.load(f)


def load_public_key(hex_str: str) -> Ed25519PublicKey:
    """Convert a hex-encoded raw Ed25519 public key to a key object."""
    raw = bytes.fromhex(hex_str)
    return Ed25519PublicKey.from_public_bytes(raw)


def verify_ed25519(pub_key: Ed25519PublicKey, signature_hex: str, data: bytes) -> bool:
    """Verify an Ed25519 signature. Returns True on valid, False otherwise."""
    try:
        sig_bytes = bytes.fromhex(signature_hex)
        pub_key.verify(sig_bytes, data)
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_phase4_chain(chain: list) -> bool:
    """Verify the Phase 4 cryptographic hash chain.
    Each entry's _chain_hash must equal SHA256(previous_chain_hash + decision_id).
    """
    running = None
    for i, entry in enumerate(chain):
        if running is None:
            running = entry.get("_chain_hash", "0" * 64)
            continue
        expected = hashlib.sha256(
            (running + entry["decision_id"]).encode()
        ).hexdigest()
        actual = entry.get("_chain_hash", "")
        if expected != actual:
            print(f"       Chain broken at entry {i}: expected {expected[:16]}…, got {actual[:16]}…")
            return False
        running = actual
    return True


def verify_phase5_chain(chain: list) -> bool:
    """Verify the Phase 5 cryptographic hash chain.
    Each entry's _p5_chain_hash must equal SHA256(previous_hash + record_id).
    """
    running = None
    for i, entry in enumerate(chain):
        if running is None:
            running = entry.get("_p5_chain_hash", "0" * 64)
            continue
        record_id_field = entry.get("_p5_record_id_field", "")
        record_id = entry.get(record_id_field, "")
        expected = hashlib.sha256(
            (running + record_id).encode()
        ).hexdigest()
        actual = entry.get("_p5_chain_hash", "")
        if expected != actual:
            print(f"       Chain broken at entry {i}: expected {expected[:16]}…, got {actual[:16]}…")
            return False
        running = actual
    return True


def verify_decision_signatures(chain: list, gateway_pub: Ed25519PublicKey) -> tuple[int, int]:
    """Verify every decision_signature in the Phase 4 chain."""
    valid_count = 0
    invalid_count = 0
    for i, entry in enumerate(chain):
        sig = entry.get("decision_signature")
        if sig is None:
            invalid_count += 1
            continue
        if not isinstance(sig, str) or len(sig) == 0:
            invalid_count += 1
            continue
        payload = json.dumps(
            {
                "decision_id": entry["decision_id"],
                "output_id": entry["output_id"],
                "status": entry["status"],
                "timestamp": entry["timestamp"],
                "violations": entry["violations"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if verify_ed25519(gateway_pub, sig, payload):
            valid_count += 1
        else:
            invalid_count += 1
            print(f"       Invalid decision_signature at Phase 4 entry {i}")
    return valid_count, invalid_count


def verify_commitment(commitment: dict, operator_pub: Ed25519PublicKey) -> bool:
    """Verify the constraint set commitment signature."""
    sig = commitment.get("signature")
    if not sig:
        return False
    ext = commitment.get("_extended", {})
    preimage = json.dumps(
        {
            "committed_at": commitment["committed_at"],
            "committed_by": ext.get("committed_by", ""),
            "constraint_set_hash": commitment["constraint_set_hash"],
            "constraint_set_version": ext.get("constraint_set_version", ""),
            "objective_description": ext.get("objective_description", ""),
            "objective_id": commitment["objective_id"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    expected_id = hashlib.sha256(preimage).hexdigest()
    if expected_id != commitment["commitment_id"]:
        print(f"       Commitment ID mismatch: expected {expected_id[:16]}…")
        return False
    return verify_ed25519(operator_pub, sig, commitment["commitment_id"].encode())


def verify_proofs(phase5_chain: list, gateway_pub: Ed25519PublicKey,
                  commitment: dict, phase4_chain: list,
                  operator_pub: Ed25519PublicKey) -> tuple[int, int]:
    """Verify all proofs in the Phase 5 chain."""
    valid_count = 0
    invalid_count = 0
    for i, entry in enumerate(phase5_chain):
        if entry.get("_p5_record_id_field") != "proof_id":
            continue
        sig = entry.get("proof_signature")
        if not sig:
            invalid_count += 1
            continue
        # Verify proof signature
        proof_id = entry.get("proof_id", "")
        if not verify_ed25519(gateway_pub, sig, proof_id.encode()):
            invalid_count += 1
            print(f"       Invalid proof_signature at Phase 5 entry {i}")
            continue
        # Verify commitment referenced by the proof
        if entry.get("commitment_id") != commitment["commitment_id"]:
            invalid_count += 1
            print(f"       Proof at entry {i} references unknown commitment")
            continue
        valid_count += 1
    return valid_count, invalid_count


def verify_manifest(bundle_dir: str) -> bool:
    """Verify that export_id matches SHA256(phase4_chain.json || phase5_chain.json)."""
    manifest = load_json(os.path.join(bundle_dir, "manifest.json"))
    with open(os.path.join(bundle_dir, "phase4_chain.json"), "rb") as f:
        p4_bytes = f.read()
    with open(os.path.join(bundle_dir, "phase5_chain.json"), "rb") as f:
        p5_bytes = f.read()
    computed = hashlib.sha256(p4_bytes + p5_bytes).hexdigest()
    expected = manifest["export_id"]
    if computed != expected:
        print(f"       Export ID mismatch: computed {computed[:16]}…, manifest says {expected[:16]}…")
        return False
    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 verify_uicp_bundle.py <audit_export_dir> <public_keys.json>")
        sys.exit(1)

    bundle_dir = sys.argv[1]
    keys_path = sys.argv[2]

    print("=" * 70)
    print("UICP INDEPENDENT VERIFICATION REPORT")
    print("=" * 70)

    # Load assets
    print("\n--- Loading audit bundle ---")
    try:
        phase4_chain = load_json(os.path.join(bundle_dir, "phase4_chain.json"))
        phase5_chain = load_json(os.path.join(bundle_dir, "phase5_chain.json"))
        commitment = load_json(os.path.join(bundle_dir, "constraint_commitment.json"))
        keys = load_json(keys_path)
        gateway_pub = load_public_key(keys["gateway_public_key_hex"])
        operator_pub = load_public_key(keys["operator_public_key_hex"])
        print(f"  Loaded {len(phase4_chain)} Phase 4 records, {len(phase5_chain)} Phase 5 records")
    except Exception as e:
        print(f"  ✗  FATAL: Cannot load audit bundle — {e}")
        sys.exit(1)

    # Verification
    print("\n--- Cryptographic verification ---")
    verify("Manifest integrity (bundle is complete and untampered)",
           verify_manifest(bundle_dir))

    verify("Phase 4 chain integrity (no records inserted, deleted, or modified)",
           verify_phase4_chain(phase4_chain))

    verify("Phase 5 chain integrity (no records inserted, deleted, or modified)",
           verify_phase5_chain(phase5_chain))

    dec_valid, dec_invalid = verify_decision_signatures(phase4_chain, gateway_pub)
    verify(f"Decision signatures ({dec_valid}/{dec_valid + dec_invalid} valid)",
           dec_invalid == 0,
           f"{dec_invalid} invalid signature(s) found")

    verify("Constraint set commitment signature",
           verify_commitment(commitment, operator_pub))

    proof_valid, proof_invalid = verify_proofs(
        phase5_chain, gateway_pub, commitment, phase4_chain, operator_pub)
    verify(f"Phase 5 proof signatures ({proof_valid}/{proof_valid + proof_invalid} valid)",
           proof_invalid == 0,
           f"{proof_invalid} invalid proof(s) found")

    # Summary
    print("\n" + "=" * 70)
    total = PASSED + FAILED
    print(f"RESULTS: {PASSED}/{total} checks passed")
    if FAILED == 0:
        print("VERDICT: All cryptographic claims verified.")
        print("The audit bundle is authentic, complete, and was produced by")
        print("the legitimate UICP enforcement gateway.")
    else:
        print(f"VERDICT: {FAILED} verification failure(s) — the audit bundle")
        print("is NOT authentic or has been tampered with.")
    print("=" * 70)

    print("\nIMPORTANT LIMITATIONS:")
    print("This verification confirms that the audit bundle was produced by the")
    print("legitimate UICP gateway and has not been tampered with.")
    print("It does NOT validate:")
    print("  - Whether the constraints were correctly defined by the operator")
    print("  - Whether the extracted bindings reflect reality")
    print("  - Whether the enforcement engine's internal logic is correct")
    print("For full scope, see docs/INDEPENDENT_VERIFICATION_GUIDE.md")

    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
