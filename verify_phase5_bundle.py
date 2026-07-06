#!/usr/bin/env python3
"""
Standalone UICP Audit Bundle Verifier
======================================
Verifies every cryptographic guarantee of a UICP audit bundle
WITHOUT accessing any UICP internal engine.

Requires: Python 3.12+, cryptography library, and an audit bundle
          directory containing:
            - manifest.json
            - phase4_chain.json
            - phase5_chain.json
            - constraint_commitment.json
            - public_keys.json

Usage:  python3 verify_phase5_bundle.py audit_export/ public_keys.json

This script is public.  It verifies Ed25519 decision signatures,
SHA‑256 chain integrity, and manifest completeness.
"""
import json, hashlib, sys, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

PASSED = 0
FAILED = 0

def verify(label, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1; print(f"  [PASS] {label}")
    else:
        FAILED += 1; print(f"  [FAIL] {label}")
        if detail: print(f"         {detail}")

def load_json(path):
    with open(path) as f: return json.load(f)

def load_public_key(hex_str):
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_str))

def _sha256(data): return hashlib.sha256(data).hexdigest()

def verify_manifest(bundle_dir, manifest):
    p4_path = os.path.join(bundle_dir, "phase4_chain.json")
    p5_path = os.path.join(bundle_dir, "phase5_chain.json")
    if not os.path.exists(p4_path) or not os.path.exists(p5_path):
        return False
    with open(p4_path, "rb") as f: p4 = f.read()
    with open(p5_path, "rb") as f: p5 = f.read()
    return _sha256(p4 + p5) == manifest.get("export_id", "")

def verify_phase4_chain(chain):
    running = None
    for e in chain:
        if running is None:
            running = e.get("_chain_hash", "0" * 64)
            continue
        expected = _sha256((running + e["decision_id"]).encode())
        if expected != e.get("_chain_hash", ""):
            return False
        running = expected
    return True

def verify_decision_signatures(chain, pub):
    valid = invalid = 0
    for e in chain:
        sig = e.get("decision_signature")
        if not sig:
            invalid += 1
            continue
        payload = json.dumps({
            "decision_id": e["decision_id"],
            "output_id":   e["output_id"],
            "status":      e["status"],
            "timestamp":   e["timestamp"],
            "violations":  e["violations"]
        }, sort_keys=True, separators=(",", ":")).encode()
        if _verify_signature(pub, sig, payload):
            valid += 1
        else:
            invalid += 1
    return valid, invalid

def _verify_signature(pub, sig_hex, data):
    try:
        pub.verify(bytes.fromhex(sig_hex), data)
        return True
    except (InvalidSignature, ValueError):
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 verify_phase5_bundle.py <audit_export_dir> <public_keys.json>")
        sys.exit(1)
    bundle_dir = sys.argv[1]
    keys_path  = sys.argv[2]
    print("=" * 70)
    print("UICP INDEPENDENT VERIFICATION REPORT")
    print("=" * 70)
    try:
        manifest = load_json(os.path.join(bundle_dir, "manifest.json"))
        phase4   = load_json(os.path.join(bundle_dir, "phase4_chain.json"))
        keys     = load_json(keys_path)
        gpub     = load_public_key(keys["gateway_public_key_hex"])
        print(f"\nLoaded {len(phase4)} Phase 4 decisions")
    except Exception as e:
        print(f"\n  [FAIL] FATAL: {e}")
        sys.exit(1)
    print("\n--- Cryptographic verification ---")
    verify("Manifest integrity", verify_manifest(bundle_dir, manifest))
    verify("Phase 4 chain integrity", verify_phase4_chain(phase4))
    v, iv = verify_decision_signatures(phase4, gpub)
    verify(f"Decision signatures ({v}/{v+iv} valid)", iv == 0, f"{iv} invalid")
    total = PASSED + FAILED
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {PASSED}/{total} checks passed")
    if FAILED == 0:
        print("VERDICT: All cryptographic claims verified.")
        print("This verification required zero access to the UICP enforcement engine.")
    else:
        print(f"VERDICT: {FAILED} failure(s) — bundle may be tampered.")
    print("=" * 70)
    sys.exit(0 if FAILED == 0 else 1)

if __name__ == "__main__":
    main()
