#!/usr/bin/env python3
"""
phase5_engine.py – UICP Phase 5 Trust & Audit Engine
GAP‑42 + GAP‑12 + GAP‑11 (two‑person signing) + 64‑test harness.
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
        return (True, None) if valid else (False, "signature verification failed – record may be tampered")
    except Exception as e: return False, f"verification error: {type(e).__name__}: {e}"

class Phase4LogRejected(Exception): pass
def accept_phase4_log(decision_log, chain_valid):
    if not isinstance(chain_valid, bool): raise Phase4LogRejected("chain_valid must be bool")
    if not chain_valid: raise Phase4LogRejected("chain_valid is False")
    if not isinstance(decision_log, list): raise Phase4LogRejected("decision_log must be list")
    return list(decision_log)

class CommitmentError(Exception): pass

class OperatorRegistry:
    def __init__(self): self._operators = {}
    def register(self, operator_id, public_key):
        if not operator_id or not isinstance(operator_id, str): raise ValueError("operator_id must be non-empty string")
        if operator_id in self._operators: raise ValueError(f"operator_id '{operator_id}' already registered")
        self._operators[operator_id] = public_key
        return self
    def is_registered(self, operator_id): return operator_id in self._operators
    def get_public_key(self, operator_id):
        if operator_id not in self._operators: raise KeyError(f"GAP-11: operator '{operator_id}' not registered")
        return self._operators[operator_id]
    def list_operators(self): return list(self._operators.keys())
    def count(self): return len(self._operators)

def create_commitment(objective_id, objective_description, constraint_set_version,
                      constraint_set_hash, committed_at, committed_by, operator_private_key,
                      operator_registry=None):
    if not objective_id or not isinstance(objective_id, str): raise CommitmentError("objective_id must be non-empty string")
    if len(constraint_set_hash) != 64: raise CommitmentError("constraint_set_hash must be 64-char hex")
    if operator_registry is not None and not operator_registry.is_registered(committed_by):
        raise PermissionError(f"GAP-11: '{committed_by}' is not a registered operator")

    preimage = {
        "objective_id": objective_id,
        "objective_description": objective_description,
        "constraint_set_hash": constraint_set_hash,
        "constraint_set_version": constraint_set_version,
        "committed_at": committed_at,
        "committed_by": committed_by,
    }
    commitment_id = _sha256(_canonical_json(preimage))
    # Sign the commitment_id (original behavior)
    signature = _sign(operator_private_key, commitment_id.encode("utf-8"))
    status = "PENDING" if operator_registry is not None else "ACTIVE"
    return {
        "objective_id": objective_id, "commitment_id": commitment_id,
        "constraint_set_hash": constraint_set_hash, "committed_at": committed_at,
        "committed_by": committed_by, "signature": signature, "status": status,
        "second_signature": None, "second_committed_by": None, "activated_at": None,
        "_extended": {"objective_description": objective_description, "constraint_set_version": constraint_set_version},
    }

def verify_commitment(commitment, operator_public_key):
    ext = commitment.get("_extended", {})
    preimage = {
        "objective_id": commitment["objective_id"],
        "objective_description": ext.get("objective_description", ""),
        "constraint_set_hash": commitment["constraint_set_hash"],
        "constraint_set_version": ext.get("constraint_set_version", ""),
        "committed_at": commitment["committed_at"],
        "committed_by": commitment["committed_by"],
    }
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
    if not identity or not isinstance(identity, str): raise OverrideError("identity must be non-empty string")
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
        rid = record.get(record_id_field, _sha256(json.dumps(record, sort_keys=True).encode()))
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
    def __init__(self, decision_log=None, chain_valid=True, last_phase4_hash=None):
        if decision_log is None: decision_log = []
        self._log = accept_phase4_log(decision_log, chain_valid)
        self._chain_valid = chain_valid
        self._index = {}
        last_phase4_hash = last_phase4_hash or "0"*64
        for rec in self._log:
            did = rec.get("decision_id")
            if did: self._index[did] = rec
        self._audit = Phase5AuditLog(phase4_last_chain_hash=last_phase4_hash)

    def commit(self, objective_id, objective_description, constraint_set_version,
               constraint_set_hash, committed_at, committed_by, operator_private_key,
               operator_registry=None):
        c = create_commitment(objective_id, objective_description, constraint_set_version,
                              constraint_set_hash, committed_at, committed_by, operator_private_key,
                              operator_registry=operator_registry)
        if c["status"] == "ACTIVE":
            self._audit.append_commitment(c)
        return c

    def countersign(self, commitment, second_operator_id, second_private_key, operator_registry):
        if commitment.get("status") != "PENDING":
            raise ValueError(f"GAP-11: commitment status is '{commitment.get('status')}' – only PENDING commitments can be countersigned")
        if not operator_registry.is_registered(second_operator_id):
            raise PermissionError(f"GAP-11: '{second_operator_id}' is not a registered operator")
        if second_operator_id == commitment["committed_by"]:
            raise PermissionError(f"GAP-11: '{second_operator_id}' cannot countersign their own commitment")
        registered_pub = operator_registry.get_public_key(second_operator_id)
        test_payload = b"key_verification"
        test_sig = _sign(second_private_key, test_payload)
        if not _verify(registered_pub, test_sig, test_payload):
            raise PermissionError(f"GAP-11: second_private_key does not match registered key for '{second_operator_id}'")

        countersign_payload = json.dumps({
            "commitment_id": commitment["commitment_id"],
            "second_committed_by": second_operator_id,
            "original_committed_by": commitment["committed_by"],
        }, sort_keys=True, separators=(",",":")).encode()
        second_signature = _sign(second_private_key, countersign_payload)
        activated_at = datetime.now(timezone.utc).isoformat()

        commitment["second_signature"] = second_signature
        commitment["second_committed_by"] = second_operator_id
        commitment["activated_at"] = activated_at
        commitment["status"] = "ACTIVE"

        activation_record = {
            "event": "COMMITMENT_ACTIVATED",
            "commitment_id": commitment["commitment_id"],
            "first_operator": commitment["committed_by"],
            "second_operator": second_operator_id,
            "activated_at": activated_at,
            "two_person_verified": True,
        }
        self._audit._append(activation_record, "commitment_id")
        return commitment

    def verify_commitment_status(self, commitment, operator_registry):
        try:
            if commitment.get("status") != "ACTIVE":
                return False, f"status is {commitment.get('status')}"

            # ── GAP-11: Integrity check – recompute commitment_id from current fields ─
            ext = commitment.get("_extended", {})
            recomputed_id = _sha256(_canonical_json({
                "objective_id": commitment["objective_id"],
                "objective_description": ext.get("objective_description", ""),
                "constraint_set_hash": commitment["constraint_set_hash"],
                "constraint_set_version": ext.get("constraint_set_version", ""),
                "committed_at": commitment["committed_at"],
                "committed_by": commitment["committed_by"],
            }))
            if recomputed_id != commitment["commitment_id"]:
                return False, "commitment has been tampered – commitment_id mismatch"

            # ── Verify first signature (over commitment_id) ─
            first_op = commitment.get("committed_by")
            if not operator_registry.is_registered(first_op):
                return False, f"first operator '{first_op}' not registered"
            first_pub = operator_registry.get_public_key(first_op)
            if not _verify(first_pub, commitment["signature"],
                           commitment["commitment_id"].encode("utf-8")):
                return False, "first signature invalid"

            # ── Verify second signature ─
            second_op = commitment.get("second_committed_by")
            if not second_op or not operator_registry.is_registered(second_op):
                return False, "second operator missing or not registered"
            second_pub = operator_registry.get_public_key(second_op)
            second_payload = json.dumps({
                "commitment_id": commitment["commitment_id"],
                "second_committed_by": second_op,
                "original_committed_by": first_op,
            }, sort_keys=True, separators=(",",":")).encode()
            if not _verify(second_pub, commitment["second_signature"], second_payload):
                return False, "second signature invalid"

            if first_op == second_op:
                return False, "same operator signed twice"

            return True, None
        except Exception as e:
            return False, f"verification error: {type(e).__name__}: {e}"

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

    def verify_commitment(self, commitment, operator_public_key):
        return verify_commitment(commitment, operator_public_key)

    def verify_proof(self, proof, gateway_public_key, commitment, decision_record, operator_public_key):
        return verify_proof(proof, gateway_public_key, commitment, decision_record, operator_public_key)

    def verify_override(self, override): return verify_override(override)

    def create_anchor(self, operator_private_key):
        timestamp    = datetime.now(timezone.utc).isoformat()
        current_hash = self._audit.last_chain_hash
        anchor_payload = json.dumps({"chain_hash":current_hash,"timestamp":timestamp}, sort_keys=True, separators=(",",":")).encode()
        anchor_id = _sha256(anchor_payload)
        anchor_signature = _sign(operator_private_key, anchor_payload)
        return {"anchor_id":anchor_id,"chain_hash":current_hash,"timestamp":timestamp,"anchor_signature":anchor_signature}

    def verify_anchor(self, anchor_record, operator_public_key):
        try:
            a_hash = anchor_record.get("chain_hash"); a_ts = anchor_record.get("timestamp")
            a_id = anchor_record.get("anchor_id"); a_sig = anchor_record.get("anchor_signature")
            if not all([a_hash, a_ts, a_id, a_sig]): return False, "missing fields"
            anchor_payload = json.dumps({"chain_hash":a_hash,"timestamp":a_ts}, sort_keys=True, separators=(",",":")).encode()
            if _sha256(anchor_payload) != a_id: return False, "anchor_id mismatch"
            if not _verify(operator_public_key, a_sig, anchor_payload): return False, "anchor signature invalid"
            if self._audit.last_chain_hash == a_hash: return True, None
            return False, f"chain hash mismatch"
        except Exception as e: return False, f"anchor verification error: {type(e).__name__}: {e}"

    @property
    def audit_log(self): return self._audit.get_log()
    @property
    def audit_chain_valid(self): return self._audit.verify_chain()
