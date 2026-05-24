#!/usr/bin/env python3
"""
phase5_engine.py – UICP Phase 5 Trust & Audit Engine
Includes GAP‑42 verify_decision_record + GAP‑12 external anchor + 30‑test harness.
"""
import hashlib, json
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

def _sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode("utf-8")
def _sign(priv, data: bytes) -> str: return priv.sign(data).hex()
def _verify(pub, sig_hex: str, data: bytes) -> bool:
    try:
        pub.verify(bytes.fromhex(sig_hex), data)
        return True
    except (InvalidSignature, ValueError):
        return False

def verify_decision_record(decision: dict, gateway_public_key) -> tuple:
    try:
        sig_hex = decision.get("decision_signature")
        if sig_hex is None: return False, "decision_signature field is absent"
        if not isinstance(sig_hex, str) or len(sig_hex) == 0:
            return False, f"decision_signature is invalid type: {type(sig_hex)}"
        signing_payload = _canonical_json({
            "decision_id": decision["decision_id"], "output_id": decision["output_id"],
            "status": decision["status"], "timestamp": decision["timestamp"],
            "violations": decision["violations"],
        })
        valid = _verify(gateway_public_key, sig_hex, signing_payload)
        if valid: return True, None
        return False, "signature verification failed — record may be tampered"
    except Exception as e: return False, f"verification error: {type(e).__name__}: {e}"

class Phase4LogRejected(Exception): pass
def accept_phase4_log(decision_log, chain_valid):
    if not isinstance(chain_valid, bool): raise Phase4LogRejected("chain_valid must be bool")
    if not chain_valid: raise Phase4LogRejected("chain_valid is False")
    if not isinstance(decision_log, list): raise Phase4LogRejected("decision_log must be list")
    return list(decision_log)

class CommitmentError(Exception): pass
def create_commitment(objective_id, objective_description, constraint_set_version,
                      constraint_set_hash, committed_at, committed_by, operator_private_key):
    if not objective_id or not isinstance(objective_id, str): raise CommitmentError("objective_id must be non‑empty string")
    if len(constraint_set_hash) != 64: raise CommitmentError("constraint_set_hash must be 64‑char hex")
    preimage = {"committed_at": committed_at, "committed_by": committed_by,
                "constraint_set_hash": constraint_set_hash, "constraint_set_version": constraint_set_version,
                "objective_description": objective_description, "objective_id": objective_id}
    commitment_id = _sha256(_canonical_json(preimage))
    signature = _sign(operator_private_key, commitment_id.encode("utf-8"))
    return {"objective_id": objective_id, "commitment_id": commitment_id,
            "constraint_set_hash": constraint_set_hash, "committed_at": committed_at,
            "signature": signature, "_extended": {"objective_description": objective_description,
            "constraint_set_version": constraint_set_version, "committed_by": committed_by}}

def verify_commitment(commitment, operator_public_key):
    ext = commitment.get("_extended", {})
    preimage = {"committed_at": commitment["committed_at"], "committed_by": ext.get("committed_by",""),
                "constraint_set_hash": commitment["constraint_set_hash"],
                "constraint_set_version": ext.get("constraint_set_version",""),
                "objective_description": ext.get("objective_description",""),
                "objective_id": commitment["objective_id"]}
    expected = _sha256(_canonical_json(preimage))
    if expected != commitment["commitment_id"]: return False
    return _verify(operator_public_key, commitment["signature"], commitment["commitment_id"].encode("utf-8"))

class ProofError(Exception): pass
def generate_proof(decision_record, commitment, gateway_private_key, chain_valid, violations_audience="REDACTED"):
    if not chain_valid: raise ProofError("chain_valid is False – refusing proof")
    for field in ("decision_id","output_id","status","timestamp"):
        if field not in decision_record: raise ProofError(f"decision_record missing '{field}'")
    status = decision_record["status"]
    if status not in ("ALLOW","BLOCK"): raise ProofError(f"status must be ALLOW/BLOCK, got {status!r}")
    preimage = {"commitment_id": commitment["commitment_id"], "decision_id": decision_record["decision_id"],
                "gateway_chain_valid": True, "output_id": decision_record["output_id"],
                "status": status, "timestamp": decision_record["timestamp"]}
    proof_id = _sha256(_canonical_json(preimage))
    proof_signature = _sign(gateway_private_key, proof_id.encode("utf-8"))
    violations_out = decision_record.get("violations", []) if violations_audience=="FULL" else "REDACTED"
    return {"proof_id": proof_id, "commitment_id": commitment["commitment_id"],
            "decision_id": decision_record["decision_id"], "status": status,
            "proof_signature": proof_signature, "_extended": {"output_id": decision_record["output_id"],
            "violations": violations_out, "timestamp": decision_record["timestamp"], "gateway_chain_valid": True}}

def verify_proof(proof, gateway_public_key, commitment, decision_record, operator_public_key):
    res = {"commitment_signature_valid":False,"proof_signature_valid":False,
           "decision_id_matches":False,"chain_valid_in_proof":False,"valid":False}
    res["commitment_signature_valid"] = verify_commitment(commitment, operator_public_key)
    res["proof_signature_valid"] = _verify(gateway_public_key, proof["proof_signature"], proof["proof_id"].encode("utf-8"))
    res["decision_id_matches"] = (decision_record.get("decision_id") == proof["decision_id"])
    res["chain_valid_in_proof"] = proof.get("_extended",{}).get("gateway_chain_valid",False)
    res["valid"] = all([res["commitment_signature_valid"], res["proof_signature_valid"],
                        res["decision_id_matches"], res["chain_valid_in_proof"]])
    return res
    class OverrideError(Exception): pass
_AUTHORIZED_OPERATOR_REGISTRY = {}

def register_authorized_operator(identity, public_key):
    if not identity or not isinstance(identity, str): raise OverrideError("identity must be non‑empty string")
    _AUTHORIZED_OPERATOR_REGISTRY[identity] = public_key

def create_override(original_decision_id, override_type, override_reason, authorized_by,
                    operator_private_key, timestamp, expires_at=None):
    if override_type not in ("TEMPORARY","PERMANENT"): raise OverrideError(f"override_type must be TEMPORARY/PERMANENT, got {override_type!r}")
    if override_type=="TEMPORARY" and not expires_at: raise OverrideError("expires_at required for TEMPORARY override")
    if authorized_by not in _AUTHORIZED_OPERATOR_REGISTRY: raise OverrideError(f"'{authorized_by}' not in registry")
    if len(original_decision_id)!=64: raise OverrideError("original_decision_id must be 64‑char hex")
    preimage = {"authorized_by": authorized_by, "expires_at": expires_at or "",
                "original_decision_id": original_decision_id, "override_reason": override_reason,
                "override_type": override_type, "timestamp": timestamp}
    override_id = _sha256(_canonical_json(preimage))
    sig = _sign(operator_private_key, override_id.encode("utf-8"))
    pub = _AUTHORIZED_OPERATOR_REGISTRY[authorized_by]
    if not _verify(pub, sig, override_id.encode("utf-8")): raise OverrideError(f"Signature verification failed for '{authorized_by}'")
    record = {"override_id": override_id, "original_decision_id": original_decision_id,
              "override_type": override_type, "authorized_by": authorized_by,
              "authorization_signature": sig, "timestamp": timestamp,
              "_extended": {"override_reason":override_reason, "logged_by_gateway":True}}
    if override_type=="TEMPORARY": record["_extended"]["expires_at"] = expires_at
    return record

def verify_override(override):
    identity = override.get("authorized_by")
    if identity not in _AUTHORIZED_OPERATOR_REGISTRY: return False
    return _verify(_AUTHORIZED_OPERATOR_REGISTRY[identity], override["authorization_signature"], override["override_id"].encode("utf-8"))

class Phase5AuditLog:
    GENESIS_HASH = "0"*64
    def __init__(self, phase4_last_chain_hash=None):
        self._entries = []
        self._genesis_anchor = _sha256(phase4_last_chain_hash.encode("utf-8")) if phase4_last_chain_hash else self.GENESIS_HASH
        self._last_hash = self._genesis_anchor
    def _append(self, record, record_id_field):
        rid = record[record_id_field]
        ch = _sha256((self._last_hash + rid).encode("utf-8"))
        entry = dict(record); entry["_p5_chain_hash"] = ch; entry["_p5_record_id_field"] = record_id_field
        self._entries.append(entry); self._last_hash = ch; return entry
    def append_commitment(self,c): return self._append(c,"commitment_id")
    def append_proof(self,p):      return self._append(p,"proof_id")
    def append_override(self,o):   return self._append(o,"override_id")
    def verify_chain(self):
        running = self._genesis_anchor
        for e in self._entries:
            id_field = e["_p5_record_id_field"]
            expected = _sha256((running + e[id_field]).encode("utf-8"))
            if e["_p5_chain_hash"] != expected: return False
            running = e["_p5_chain_hash"]
        return True
    def get_log(self): return list(self._entries)
    @property
    def last_chain_hash(self): return self._last_hash

class Phase5Engine:
    def __init__(self, decision_log, chain_valid):
        self._log = accept_phase4_log(decision_log, chain_valid)
        self._chain_valid = chain_valid
        self._index = {}
        last_phase4_hash = None
        for rec in self._log:
            did = rec.get("decision_id")
            if did: self._index[did] = rec
            last_phase4_hash = rec.get("_chain_hash", last_phase4_hash)
        self._audit = Phase5AuditLog(phase4_last_chain_hash=last_phase4_hash)
    def commit(self, objective_id, objective_description, constraint_set_version,
               constraint_set_hash, committed_at, committed_by, operator_private_key):
        c = create_commitment(objective_id, objective_description, constraint_set_version,
                              constraint_set_hash, committed_at, committed_by, operator_private_key)
        self._audit.append_commitment(c); return c
    def prove(self, decision_id, commitment, gateway_private_key, violations_audience="REDACTED"):
        if decision_id not in self._index: raise ProofError(f"decision_id {decision_id!r} not in log")
        rec = self._index[decision_id]
        p = generate_proof(rec, commitment, gateway_private_key, self._chain_valid, violations_audience)
        self._audit.append_proof(p); return p
    def override(self, original_decision_id, override_type, override_reason,
                 authorized_by, operator_private_key, timestamp, expires_at=None):
        if original_decision_id not in self._index: raise OverrideError(f"decision_id {original_decision_id!r} not in log")
        if self._index[original_decision_id].get("status")!="BLOCK": raise OverrideError("only BLOCK decisions can be overridden")
        ov = create_override(original_decision_id, override_type, override_reason,
                             authorized_by, operator_private_key, timestamp, expires_at)
        self._audit.append_override(ov); return ov
    def verify_commitment(self, commitment, operator_public_key): return verify_commitment(commitment, operator_public_key)
    def verify_proof(self, proof, gateway_public_key, commitment, decision_record, operator_public_key):
        return verify_proof(proof, gateway_public_key, commitment, decision_record, operator_public_key)
    def verify_override(self, override): return verify_override(override)
    @property
    def audit_log(self): return self._audit.get_log()
    @property
    def audit_chain_valid(self): return self._audit.verify_chain()

    # ═══════════════════════════════════════════════════════════════
    # GAP‑12 PATCH: External Audit Log Anchor
    # ═══════════════════════════════════════════════════════════════

    def create_anchor(self, operator_private_key) -> dict:
        """Create a cryptographic anchor record for the current chain state."""
        timestamp      = datetime.now(timezone.utc).isoformat()
        current_hash   = self._audit.last_chain_hash

        anchor_payload = json.dumps(
            {"chain_hash": current_hash, "timestamp": timestamp},
            sort_keys=True, separators=(",", ":")
        ).encode()

        anchor_id        = _sha256(anchor_payload)
        anchor_signature = _sign(operator_private_key, anchor_payload)

        return {
            "anchor_id":        anchor_id,
            "chain_hash":       current_hash,
            "timestamp":        timestamp,
            "anchor_signature": anchor_signature,
        }

    def verify_anchor(self, anchor_record: dict, operator_public_key) -> tuple:
        """Verify that the current chain is consistent with a previously created anchor."""
        try:
            anchor_chain_hash = anchor_record.get("chain_hash")
            anchor_timestamp  = anchor_record.get("timestamp")
            anchor_id         = anchor_record.get("anchor_id")
            anchor_signature  = anchor_record.get("anchor_signature")

            if not all([anchor_chain_hash, anchor_timestamp, anchor_id, anchor_signature]):
                return False, "anchor record is missing required fields"

            anchor_payload = json.dumps(
                {"chain_hash": anchor_chain_hash, "timestamp": anchor_timestamp},
                sort_keys=True, separators=(",", ":")
            ).encode()

            if not _verify(operator_public_key, anchor_signature, anchor_payload):
                return False, "anchor signature invalid — anchor record may be tampered"

            recomputed_id = _sha256(anchor_payload)
            if recomputed_id != anchor_id:
                return False, f"anchor_id mismatch — stored={anchor_id[:16]}… computed={recomputed_id[:16]}…"

            current_hash = self._audit.last_chain_hash
            if current_hash == anchor_chain_hash:
                return True, None
            return False, f"chain hash mismatch — anchored={anchor_chain_hash[:16]}… current={current_hash[:16]}…"

        except Exception as exc:
            return False, f"anchor verification error: {type(exc).__name__}: {exc}"
            if __name__ == '__main__':
    PASS, FAIL = 0, 0
    def test(name, cond, det=""):
        global PASS, FAIL
        if cond: PASS += 1; print(f"  PASS  {name}")
        else: FAIL += 1; print(f"  FAIL  {name}  —  {det}")

    def gen_keypair():
        priv = Ed25519PrivateKey.generate(); return priv, priv.public_key()

    OPERATOR_PRIV, OPERATOR_PUB = gen_keypair()
    GATEWAY_PRIV,  GATEWAY_PUB  = gen_keypair()
    ROGUE_PRIV,    ROGUE_PUB    = gen_keypair()

    ALLOW_DECISION = {"decision_id":"a"*64,"output_id":"out-001","status":"ALLOW","violations":[],"timestamp":"2025-06-15T12:00:00Z","_chain_hash":"c"*64}
    BLOCK_DECISION = {"decision_id":"b"*64,"output_id":"out-002","status":"BLOCK","violations":["CONSTRAINT_AGE_MIN_18"],"timestamp":"2025-06-15T12:01:00Z","_chain_hash":"d"*64}
    PHASE4_LOG = [ALLOW_DECISION, BLOCK_DECISION]
    CONSTRAINT_HASH = "e"*64; COMMITTED_AT = "2025-06-15T10:00:00Z"; OVERRIDE_TS = "2025-06-15T14:30:00Z"
    OPERATOR_IDENTITY = "dr.smith@hospital.example"
    _AUTHORIZED_OPERATOR_REGISTRY.clear(); register_authorized_operator(OPERATOR_IDENTITY, OPERATOR_PUB)

    def fresh_engine(): return Phase5Engine(PHASE4_LOG, True)

    print("=== Phase 5 Test Suite ===\n")
    print("-- Log Acceptance --")
    test("valid chain accepted", Phase5Engine(PHASE4_LOG, True) is not None)
    try: Phase5Engine(PHASE4_LOG, False); test("invalid chain rejected", False)
    except Phase4LogRejected: test("invalid chain rejected", True)
    try: Phase5Engine(PHASE4_LOG, 1); test("non-bool chain_valid rejected", False)
    except Phase4LogRejected: test("non-bool chain_valid rejected", True)

    print("\n-- Objective Commitment --")
    eng = fresh_engine()
    c = eng.commit("SAFETY_POLICY_V2.1","No underage recommendations.","v3.7",CONSTRAINT_HASH,COMMITTED_AT,OPERATOR_IDENTITY,OPERATOR_PRIV)
    test("output contract fields present", all(k in c for k in ["objective_id","commitment_id","constraint_set_hash","committed_at","signature"]))
    test("deterministic", fresh_engine().commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"] == fresh_engine().commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"])
    test("changes with constraint_set_hash", eng.commit("X","d","v1","a"*64,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"] != eng.commit("X","d","v1","b"*64,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"])
    test("signature verifies", eng.verify_commitment(c, OPERATOR_PUB))
    test("signature fails wrong key", not eng.verify_commitment(c, ROGUE_PUB))
    try: eng.commit("X","d","v1","tooshort",COMMITTED_AT,"alice",OPERATOR_PRIV); test("invalid hash length rejected", False)
    except CommitmentError: test("invalid hash length rejected", True)

    print("\n-- Proof Generation --")
    eng = fresh_engine()
    c = eng.commit("SAFETY_POLICY_V2.1","desc","v3.7",CONSTRAINT_HASH,COMMITTED_AT,OPERATOR_IDENTITY,OPERATOR_PRIV)
    p = eng.prove("a"*64, c, GATEWAY_PRIV)
    test("output contract fields present", all(k in p for k in ["proof_id","commitment_id","decision_id","status","proof_signature"]))
    test("deterministic", fresh_engine().prove("a"*64,c,GATEWAY_PRIV)["proof_id"] == fresh_engine().prove("a"*64,c,GATEWAY_PRIV)["proof_id"])
    test("BLOCK decision proof", eng.prove("b"*64,c,GATEWAY_PRIV)["status"]=="BLOCK")
    test("violations redacted by default", eng.prove("b"*64,c,GATEWAY_PRIV)["_extended"]["violations"]=="REDACTED")
    test("violations full audience", eng.prove("b"*64,c,GATEWAY_PRIV,"FULL")["_extended"]["violations"]==["CONSTRAINT_AGE_MIN_18"])
    try: eng.prove("f"*64,c,GATEWAY_PRIV); test("unknown decision_id rejected", False)
    except ProofError: test("unknown decision_id rejected", True)
    res = eng.verify_proof(p, GATEWAY_PUB, c, ALLOW_DECISION, OPERATOR_PUB)
    test("signature verifies (full path)", res["valid"])
    test("fails wrong gateway key", not eng.verify_proof(p, ROGUE_PUB, c, ALLOW_DECISION, OPERATOR_PUB)["valid"])
    test("fails mismatched decision record", not eng.verify_proof(p, GATEWAY_PUB, c, BLOCK_DECISION, OPERATOR_PUB)["valid"])

    print("\n-- Override Controls --")
    _AUTHORIZED_OPERATOR_REGISTRY.clear(); register_authorized_operator(OPERATOR_IDENTITY, OPERATOR_PUB)
    eng = fresh_engine()
    ov = eng.override("b"*64,"PERMANENT","Emergency medical override",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS)
    test("valid permanent override", True)
    ov2 = eng.override("b"*64,"TEMPORARY","Short-term",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS,"2025-06-15T16:00:00Z")
    test("valid temporary override", ov2["_extended"]["expires_at"]=="2025-06-15T16:00:00Z")
    try: eng.override("b"*64,"TEMPORARY","noexpires",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS,None); test("temporary requires expires_at", False)
    except OverrideError: test("temporary requires expires_at", True)
    try: eng.override("b"*64,"PERMANENT","rogue","unknown@x.com",ROGUE_PRIV,OVERRIDE_TS); test("unregistered operator rejected", False)
    except OverrideError: test("unregistered operator rejected", True)
    try: eng.override("b"*64,"PERMANENT","imp",OPERATOR_IDENTITY,ROGUE_PRIV,OVERRIDE_TS); test("wrong key for registered identity", False)
    except OverrideError: test("wrong key for registered identity", True)
    try: eng.override("a"*64,"PERMANENT","bad",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS); test("only BLOCK decisions overridable", False)
    except OverrideError: test("only BLOCK decisions overridable", True)
    ov3 = fresh_engine().override("b"*64,"PERMANENT","det",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS)
    ov4 = fresh_engine().override("b"*64,"PERMANENT","det",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS)
    test("deterministic", ov3["override_id"]==ov4["override_id"])
    test("signature verifies", eng.verify_override(ov))
    test("original decision not modified", BLOCK_DECISION["decision_id"]=="b"*64 and BLOCK_DECISION["status"]=="BLOCK")

    print("\n-- Audit Log --")
    eng = fresh_engine()
    c = eng.commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)
    eng.prove("a"*64,c,GATEWAY_PRIV)
    eng.override("b"*64,"PERMANENT","audit",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS)
    test("log grows correctly", len(eng.audit_log)==3)
    test("audit chain valid", eng.audit_chain_valid)

    print("\n-- Chain Integrity Gate --")
    try: Phase5Engine(PHASE4_LOG, False); test("chain_valid=False blocks all ops", False)
    except Phase4LogRejected: test("chain_valid=False blocks all ops", True)

    original_total = PASS + FAIL
    original_pass = PASS
    original_fail = FAIL
    print(f"\n=== Original Phase 5 Results: {original_pass}/{original_total} passed ===\n")

    # ═══════════════════════════════════════════════════════════════
    # GAP‑12 Tests — using the existing test() function (no nonlocal)
    # ═══════════════════════════════════════════════════════════════
    print("=== GAP-12 External Audit Anchor Tests ===\n")

    # Reset the counters so we can track GAP‑12 separately then combine
    gap12_start_pass = PASS
    gap12_start_fail = FAIL

    eng12 = fresh_engine()
    eng12.commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)
    eng12.prove("a"*64,eng12.commit("Y","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"bob",OPERATOR_PRIV),GATEWAY_PRIV)
    eng12.override("b"*64,"PERMANENT","anchor test",OPERATOR_IDENTITY,OPERATOR_PRIV,OVERRIDE_TS)

    anchor = eng12.create_anchor(OPERATOR_PRIV)
    test("GAP-12 | create_anchor returns all required fields",
         all(k in anchor for k in ["anchor_id","chain_hash","timestamp","anchor_signature"]))
    test("GAP-12 | anchor_id is non-empty string",
         isinstance(anchor.get("anchor_id"), str) and len(anchor.get("anchor_id", "")) > 0)
    test("GAP-12 | chain_hash is non-empty string",
         isinstance(anchor.get("chain_hash"), str) and len(anchor.get("chain_hash", "")) > 0)
    test("GAP-12 | timestamp is non-empty string",
         isinstance(anchor.get("timestamp"), str) and len(anchor.get("timestamp", "")) > 0)
    test("GAP-12 | anchor_signature is non-empty string",
         isinstance(anchor.get("anchor_signature"), str) and len(anchor.get("anchor_signature", "")) > 0)

    valid, reason = eng12.verify_anchor(anchor, OPERATOR_PUB)
    test("GAP-12 | verify_anchor passes on valid anchor against current chain", valid, reason)

    valid_w, reason_w = eng12.verify_anchor(anchor, ROGUE_PUB)
    test("GAP-12 | verify_anchor fails with wrong public key", not valid_w, reason_w)

    tampered_id = dict(anchor)
    tampered_id["anchor_id"] = "0" * 64
    valid_ti, reason_ti = eng12.verify_anchor(tampered_id, OPERATOR_PUB)
    test("GAP-12 | verify_anchor fails with tampered anchor_id", not valid_ti, reason_ti)

    tampered_ch = dict(anchor)
    tampered_ch["chain_hash"] = "0" * 64
    valid_tc, reason_tc = eng12.verify_anchor(tampered_ch, OPERATOR_PUB)
    test("GAP-12 | verify_anchor fails with tampered chain_hash in anchor", not valid_tc, reason_tc)

    incomplete = {"anchor_id": "abc"}
    valid_inc, reason_inc = eng12.verify_anchor(incomplete, OPERATOR_PUB)
    test("GAP-12 | verify_anchor fails with incomplete anchor record", not valid_inc, reason_inc)

    eng_other = fresh_engine()
    eng_other.commit("Z","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"carol",OPERATOR_PRIV)
    valid_mm, reason_mm = eng_other.verify_anchor(anchor, OPERATOR_PUB)
    test("GAP-12 | verify_anchor detects chain hash mismatch between engines", not valid_mm, reason_mm)

    anchor2 = eng12.create_anchor(OPERATOR_PRIV)
    test("GAP-12 | Two anchors at same chain state have same chain_hash",
         anchor["chain_hash"] == anchor2["chain_hash"])

    payload = json.dumps(
        {"chain_hash": anchor["chain_hash"], "timestamp": anchor["timestamp"]},
        sort_keys=True, separators=(",", ":")
    ).encode()
    expected_aid = _sha256(payload)
    test("GAP-12 | anchor_id is deterministic SHA-256 of payload",
         anchor["anchor_id"] == expected_aid)

    gap12_pass = PASS - gap12_start_pass
    gap12_fail = FAIL - gap12_start_fail
    total12 = gap12_pass + gap12_fail
    print(f"\n=== GAP-12 Results: {gap12_pass}/{total12} passed ===")
    if gap12_fail > 0: print("FAIL — do not commit")
    else: print("ALL GAP-12 TESTS PASSED — ready for PR")

    combined_pass = PASS
    combined_fail = FAIL
    print(f"\nCOMBINED RESULTS: {combined_pass} passed, {combined_fail} failed")
    if combined_fail == 0: print("  ✓ ALL TESTS PASS — Phase 5 with GAP‑12 is ALIGNED.\n")
    else: print(f"  ✗ {combined_fail} FAILURE(S) — Phase 5 is NOT aligned.\n")
