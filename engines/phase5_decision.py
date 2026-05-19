#!/usr/bin/env python3
"""
Phase 5 – Trust & Audit Engine (Colab‑ready, monolithic)
"""
import hashlib, json
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey
)
from cryptography.exceptions import InvalidSignature

# ----- cryptographic helpers -----
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True).encode("utf-8")

def _sign(priv, data: bytes) -> str:
    return priv.sign(data).hex()

def _verify(pub, sig_hex: str, data: bytes) -> bool:
    try:
        pub.verify(bytes.fromhex(sig_hex), data)
        return True
    except (InvalidSignature, ValueError):
        return False

# ----- gate -----
class Phase4LogRejected(Exception): pass

def accept_phase4_log(decision_log, chain_valid):
    if not isinstance(chain_valid, bool):
        raise Phase4LogRejected("chain_valid must be bool")
    if not chain_valid:
        raise Phase4LogRejected("chain_valid is False")
    if not isinstance(decision_log, list):
        raise Phase4LogRejected("decision_log must be list")
    return list(decision_log)

# ----- commitment -----
class CommitmentError(Exception): pass

def create_commitment(objective_id, objective_description, constraint_set_version,
                      constraint_set_hash, committed_at, committed_by, operator_private_key):
    if not objective_id or not isinstance(objective_id, str):
        raise CommitmentError("objective_id must be non‑empty string")
    if len(constraint_set_hash) != 64:
        raise CommitmentError("constraint_set_hash must be 64‑char hex")
    preimage = {
        "committed_at": committed_at,
        "committed_by": committed_by,
        "constraint_set_hash": constraint_set_hash,
        "constraint_set_version": constraint_set_version,
        "objective_description": objective_description,
        "objective_id": objective_id,
    }
    commitment_id = _sha256(_canonical_json(preimage))
    signature = _sign(operator_private_key, commitment_id.encode("utf-8"))
    return {
        "objective_id": objective_id,
        "commitment_id": commitment_id,
        "constraint_set_hash": constraint_set_hash,
        "committed_at": committed_at,
        "signature": signature,
        "_extended": {
            "objective_description": objective_description,
            "constraint_set_version": constraint_set_version,
            "committed_by": committed_by,
        },
    }

def verify_commitment(commitment, operator_public_key):
    ext = commitment.get("_extended", {})
    preimage = {
        "committed_at": commitment["committed_at"],
        "committed_by": ext.get("committed_by", ""),
        "constraint_set_hash": commitment["constraint_set_hash"],
        "constraint_set_version": ext.get("constraint_set_version", ""),
        "objective_description": ext.get("objective_description", ""),
        "objective_id": commitment["objective_id"],
    }
    expected = _sha256(_canonical_json(preimage))
    if expected != commitment["commitment_id"]:
        return False
    return _verify(operator_public_key, commitment["signature"], commitment["commitment_id"].encode("utf-8"))
  # ----- proof -----
class ProofError(Exception): pass

def generate_proof(decision_record, commitment, gateway_private_key, chain_valid, violations_audience="REDACTED"):
    if not chain_valid:
        raise ProofError("chain_valid is False – refusing proof")
    for field in ("decision_id","output_id","status","timestamp"):
        if field not in decision_record:
            raise ProofError(f"decision_record missing '{field}'")
    status = decision_record["status"]
    if status not in ("ALLOW","BLOCK"):
        raise ProofError(f"status must be ALLOW/BLOCK, got {status!r}")
    preimage = {
        "commitment_id": commitment["commitment_id"],
        "decision_id": decision_record["decision_id"],
        "gateway_chain_valid": True,
        "output_id": decision_record["output_id"],
        "status": status,
        "timestamp": decision_record["timestamp"],
    }
    proof_id = _sha256(_canonical_json(preimage))
    proof_signature = _sign(gateway_private_key, proof_id.encode("utf-8"))
    violations_out = decision_record.get("violations", []) if violations_audience=="FULL" else "REDACTED"
    return {
        "proof_id": proof_id,
        "commitment_id": commitment["commitment_id"],
        "decision_id": decision_record["decision_id"],
        "status": status,
        "proof_signature": proof_signature,
        "_extended": {
            "output_id": decision_record["output_id"],
            "violations": violations_out,
            "timestamp": decision_record["timestamp"],
            "gateway_chain_valid": True,
        },
    }

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

# ----- override -----
class OverrideError(Exception): pass
_AUTHORIZED_OPERATOR_REGISTRY = {}

def register_authorized_operator(identity, public_key):
    if not identity or not isinstance(identity, str):
        raise OverrideError("identity must be non‑empty string")
    _AUTHORIZED_OPERATOR_REGISTRY[identity] = public_key

def create_override(original_decision_id, override_type, override_reason, authorized_by,
                    operator_private_key, timestamp, expires_at=None):
    if override_type not in ("TEMPORARY","PERMANENT"):
        raise OverrideError(f"override_type must be TEMPORARY/PERMANENT, got {override_type!r}")
    if override_type=="TEMPORARY" and not expires_at:
        raise OverrideError("expires_at required for TEMPORARY override")
    if authorized_by not in _AUTHORIZED_OPERATOR_REGISTRY:
        raise OverrideError(f"'{authorized_by}' not in registry")
    if len(original_decision_id)!=64:
        raise OverrideError("original_decision_id must be 64‑char hex")
    preimage = {
        "authorized_by": authorized_by,
        "expires_at": expires_at or "",
        "original_decision_id": original_decision_id,
        "override_reason": override_reason,
        "override_type": override_type,
        "timestamp": timestamp,
    }
    override_id = _sha256(_canonical_json(preimage))
    sig = _sign(operator_private_key, override_id.encode("utf-8"))
    pub = _AUTHORIZED_OPERATOR_REGISTRY[authorized_by]
    if not _verify(pub, sig, override_id.encode("utf-8")):
        raise OverrideError(f"Signature verification failed for '{authorized_by}'")
    record = {
        "override_id": override_id,
        "original_decision_id": original_decision_id,
        "override_type": override_type,
        "authorized_by": authorized_by,
        "authorization_signature": sig,
        "timestamp": timestamp,
        "_extended": {"override_reason":override_reason, "logged_by_gateway":True},
    }
    if override_type=="TEMPORARY":
        record["_extended"]["expires_at"] = expires_at
    return record

def verify_override(override):
    identity = override.get("authorized_by")
    if identity not in _AUTHORIZED_OPERATOR_REGISTRY:
        return False
    return _verify(_AUTHORIZED_OPERATOR_REGISTRY[identity],
                   override["authorization_signature"],
                   override["override_id"].encode("utf-8"))

# ----- audit log -----
class Phase5AuditLog:
    GENESIS_HASH = "0"*64
    def __init__(self, phase4_last_chain_hash=None):
        self._entries = []
        self._genesis_anchor = _sha256(phase4_last_chain_hash.encode("utf-8")) if phase4_last_chain_hash else self.GENESIS_HASH
        self._last_hash = self._genesis_anchor
    def _append(self, record, record_id_field):
        rid = record[record_id_field]
        ch = _sha256((self._last_hash + rid).encode("utf-8"))
        entry = dict(record)
        entry["_p5_chain_hash"] = ch
        entry["_p5_record_id_field"] = record_id_field
        self._entries.append(entry)
        self._last_hash = ch
        return entry
    def append_commitment(self,c): return self._append(c,"commitment_id")
    def append_proof(self,p):      return self._append(p,"proof_id")
    def append_override(self,o):   return self._append(o,"override_id")
    def verify_chain(self):
        running = self._genesis_anchor
        for e in self._entries:
            id_field = e["_p5_record_id_field"]
            expected = _sha256((running + e[id_field]).encode("utf-8"))
            if e["_p5_chain_hash"] != expected:
                return False
            running = e["_p5_chain_hash"]
        return True
    def get_log(self): return list(self._entries)
    @property
    def last_chain_hash(self): return self._last_hash
      # ----- top‑level engine -----
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
        self._audit.append_commitment(c)
        return c
    def prove(self, decision_id, commitment, gateway_private_key, violations_audience="REDACTED"):
        if decision_id not in self._index:
            raise ProofError(f"decision_id {decision_id!r} not in log")
        rec = self._index[decision_id]
        p = generate_proof(rec, commitment, gateway_private_key, self._chain_valid, violations_audience)
        self._audit.append_proof(p)
        return p
    def override(self, original_decision_id, override_type, override_reason,
                 authorized_by, operator_private_key, timestamp, expires_at=None):
        if original_decision_id not in self._index:
            raise OverrideError(f"decision_id {original_decision_id!r} not in log")
        if self._index[original_decision_id].get("status")!="BLOCK":
            raise OverrideError("only BLOCK decisions can be overridden")
        ov = create_override(original_decision_id, override_type, override_reason,
                             authorized_by, operator_private_key, timestamp, expires_at)
        self._audit.append_override(ov)
        return ov
    def verify_commitment(self, commitment, operator_public_key):
        return verify_commitment(commitment, operator_public_key)
    def verify_proof(self, proof, gateway_public_key, commitment, decision_record, operator_public_key):
        return verify_proof(proof, gateway_public_key, commitment, decision_record, operator_public_key)
    def verify_override(self, override):
        return verify_override(override)
    @property
    def audit_log(self): return self._audit.get_log()
    @property
    def audit_chain_valid(self): return self._audit.verify_chain()


# ---------------------------------------------------------------------------
# TEST HARNESS (30 tests)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    PASS = FAIL = 0
    def test(name, cond, det=""):
        global PASS, FAIL
        if cond:
            PASS += 1; print(f"  PASS  {name}")
        else:
            FAIL += 1; print(f"  FAIL  {name}  —  {det}")

    def gen_keypair():
        priv = Ed25519PrivateKey.generate()
        return priv, priv.public_key()

    OPERATOR_PRIV, OPERATOR_PUB = gen_keypair()
    GATEWAY_PRIV,  GATEWAY_PUB  = gen_keypair()
    ROGUE_PRIV,    ROGUE_PUB    = gen_keypair()

    ALLOW_DECISION = {
        "decision_id": "a" * 64, "output_id": "out-001", "status": "ALLOW",
        "violations": [], "timestamp": "2025-06-15T12:00:00Z", "_chain_hash": "c" * 64,
    }
    BLOCK_DECISION = {
        "decision_id": "b" * 64, "output_id": "out-002", "status": "BLOCK",
        "violations": ["CONSTRAINT_AGE_MIN_18"], "timestamp": "2025-06-15T12:01:00Z", "_chain_hash": "d" * 64,
    }
    PHASE4_LOG = [ALLOW_DECISION, BLOCK_DECISION]
    CONSTRAINT_HASH = "e" * 64
    COMMITTED_AT = "2025-06-15T10:00:00Z"
    OVERRIDE_TS   = "2025-06-15T14:30:00Z"
    OPERATOR_IDENTITY = "dr.smith@hospital.example"

    _AUTHORIZED_OPERATOR_REGISTRY.clear()
    register_authorized_operator(OPERATOR_IDENTITY, OPERATOR_PUB)

    def fresh_engine():
        return Phase5Engine(PHASE4_LOG, chain_valid=True)

    print("=== Phase 5 Test Suite ===\n")

    print("-- Log Acceptance --")
    test("valid chain accepted",
         Phase5Engine(PHASE4_LOG, chain_valid=True) is not None)
    try: Phase5Engine(PHASE4_LOG, chain_valid=False); test("invalid chain rejected", False)
    except Phase4LogRejected: test("invalid chain rejected", True)
    try: Phase5Engine(PHASE4_LOG, chain_valid=1); test("non-bool chain_valid rejected", False)
    except Phase4LogRejected: test("non-bool chain_valid rejected", True)

    print("\n-- Objective Commitment --")
    eng = fresh_engine()
    c = eng.commit("SAFETY_POLICY_V2.1","No underage recommendations.","v3.7",
                   CONSTRAINT_HASH, COMMITTED_AT, OPERATOR_IDENTITY, OPERATOR_PRIV)
    test("output contract fields present",
         all(k in c for k in ["objective_id","commitment_id","constraint_set_hash","committed_at","signature"]))
    test("deterministic", (lambda e=fresh_engine(): e.commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"]
                            == fresh_engine().commit("X","d","v1",CONSTRAINT_HASH,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"])())
    test("changes with constraint_set_hash",
         eng.commit("X","d","v1","a"*64,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"]
         != eng.commit("X","d","v1","b"*64,COMMITTED_AT,"alice",OPERATOR_PRIV)["commitment_id"])
    test("signature verifies", eng.verify_commitment(c, OPERATOR_PUB))
    test("signature fails wrong key", not eng.verify_commitment(c, ROGUE_PUB))
    try: eng.commit("X","d","v1","tooshort",COMMITTED_AT,"alice",OPERATOR_PRIV); test("invalid hash length rejected", False)
    except CommitmentError: test("invalid hash length rejected", True)

    print("\n-- Proof Generation --")
    eng = fresh_engine()
    c = eng.commit("SAFETY_POLICY_V2.1","desc","v3.7",CONSTRAINT_HASH,COMMITTED_AT,OPERATOR_IDENTITY,OPERATOR_PRIV)
    p = eng.prove("a"*64, c, GATEWAY_PRIV)
    test("output contract fields present",
         all(k in p for k in ["proof_id","commitment_id","decision_id","status","proof_signature"]))
    test("deterministic", (lambda e=fresh_engine(),c=c: e.prove("a"*64,c,GATEWAY_PRIV)["proof_id"]
                            == fresh_engine().prove("a"*64,c,GATEWAY_PRIV)["proof_id"])())
    test("BLOCK decision proof", eng.prove("b"*64,c,GATEWAY_PRIV)["status"]=="BLOCK")
    test("violations redacted by default", eng.prove("b"*64,c,GATEWAY_PRIV)["_extended"]["violations"]=="REDACTED")
    test("violations full audience", eng.prove("b"*64,c,GATEWAY_PRIV,violations_audience="FULL")["_extended"]["violations"]==["CONSTRAINT_AGE_MIN_18"])
    try: eng.prove("f"*64,c,GATEWAY_PRIV); test("unknown decision_id rejected", False)
    except ProofError: test("unknown decision_id rejected", True)
    res = eng.verify_proof(p, GATEWAY_PUB, c, ALLOW_DECISION, OPERATOR_PUB)
    test("signature verifies (full path)", res["valid"])
    test("fails wrong gateway key", not eng.verify_proof(p, ROGUE_PUB, c, ALLOW_DECISION, OPERATOR_PUB)["valid"])
    test("fails mismatched decision record", not eng.verify_proof(p, GATEWAY_PUB, c, BLOCK_DECISION, OPERATOR_PUB)["valid"])

    print("\n-- Override Controls --")
    _AUTHORIZED_OPERATOR_REGISTRY.clear()
    register_authorized_operator(OPERATOR_IDENTITY, OPERATOR_PUB)
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
    try: Phase5Engine(PHASE4_LOG, chain_valid=False); test("chain_valid=False blocks all ops", False)
    except Phase4LogRejected: test("chain_valid=False blocks all ops", True)

    total = PASS + FAIL
    print(f"\n=== Results: {PASS}/{total} passed ===\n")
    import sys
    sys.exit(0 if FAIL == 0 else 1)
