#!/usr/bin/env python3
"""
phase5_engine.py – UICP Phase 5 Trust & Audit Engine
GAP‑42 + GAP‑12 + GAP‑11 + GAP‑13/14 + 89‑test harness.
"""
import hashlib, json, os
from datetime import datetime, timezone, timedelta
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

# ═══════════════════ GAP‑13 + GAP‑14: KeyLifecycleManager ═══════════════════
class KeyLifecycleManager:
    STATUS_ACTIVE  = "ACTIVE"
    STATUS_ROTATED = "ROTATED"
    STATUS_REVOKED = "REVOKED"
    STATUS_EXPIRED = "EXPIRED"
    DEFAULT_VALIDITY_MONTHS = 12

    def __init__(self, validity_months: int = DEFAULT_VALIDITY_MONTHS):
        if validity_months < 1 or validity_months > 120:
            raise ValueError("validity_months must be between 1 and 120")
        self._validity_months = validity_months
        self._keys: dict = {}

    @staticmethod
    def compute_key_id(public_key) -> str:
        import hashlib
        pub_bytes = public_key.public_bytes_raw()
        return hashlib.sha256(pub_bytes).hexdigest()

    def generate_key(self, operator_id: str, environment: str = "development") -> dict:
        if environment not in ("development", "staging", "production"):
            raise ValueError("environment must be: development, staging, or production")
        private_key = Ed25519PrivateKey.generate()
        public_key  = private_key.public_key()
        key_id      = self.compute_key_id(public_key)
        now         = datetime.now(timezone.utc)
        expires_at  = now + timedelta(days=self._validity_months * 30)
        key_record = {
            "key_id":         key_id,
            "operator_id":    operator_id,
            "environment":    environment,
            "status":         self.STATUS_ACTIVE,
            "created_at":     now.isoformat(),
            "expires_at":     expires_at.isoformat(),
            "rotated_at":     None,
            "revoked_at":     None,
            "revocation_reason": None,
            "replaced_by":    None,
            "replaces":       None,
            "validity_months": self._validity_months,
            "_private_key":   private_key,
            "_public_key":    public_key,
            "storage_spec":   self._storage_spec(environment),
        }
        self._keys[key_id] = key_record
        return key_record

    @staticmethod
    def _storage_spec(environment: str) -> str:
        specs = {
            "development": "IN-MEMORY ONLY. Keys are ephemeral. Fresh key pair generated each session. Acceptable for development and testing only.",
            "staging": "ENCRYPTED FILE. AES-256-GCM. Encryption key stored in environment variable KEY_ENCRYPTION_KEY — never in the same file. File path: /secrets/operator_key.enc Rotate every 12 months or on suspected compromise.",
            "production": "HARDWARE SECURITY MODULE (HSM) or KMS REQUIRED. Private key never leaves the HSM. Sign operations are performed inside the HSM. Public key exported for verification. Acceptable alternatives: AWS KMS, Azure Key Vault, Google Cloud KMS, HashiCorp Vault with HSM backend. NEVER store production private keys in files or env vars.",
        }
        return specs.get(environment, "UNKNOWN ENVIRONMENT")

    def get_status(self, key_id: str) -> str:
        if key_id not in self._keys:
            raise KeyError(f"key_id '{key_id}' not found in registry")
        record = self._keys[key_id]
        if record["status"] == self.STATUS_REVOKED:
            return self.STATUS_REVOKED
        if record["status"] == self.STATUS_ROTATED:
            return self.STATUS_ROTATED
        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            self._keys[key_id]["status"] = self.STATUS_EXPIRED
            return self.STATUS_EXPIRED
        return self.STATUS_ACTIVE

    def is_valid_for_signing(self, key_id: str) -> bool:
        return self.get_status(key_id) == self.STATUS_ACTIVE

    def is_valid_for_verification(self, key_id: str) -> bool:
        status = self.get_status(key_id)
        return status in (self.STATUS_ACTIVE, self.STATUS_ROTATED, self.STATUS_EXPIRED)

    def rotate(self, old_key_id: str, operator_id: str, environment: str = "development") -> dict:
        if old_key_id not in self._keys:
            raise KeyError(f"key_id '{old_key_id}' not found")
        old_status = self.get_status(old_key_id)
        if old_status == self.STATUS_REVOKED:
            raise ValueError("Cannot rotate a REVOKED key — generate a new key instead")
        new_record = self.generate_key(operator_id, environment)
        new_key_id = new_record["key_id"]
        now = datetime.now(timezone.utc).isoformat()
        self._keys[old_key_id]["status"]      = self.STATUS_ROTATED
        self._keys[old_key_id]["rotated_at"]  = now
        self._keys[old_key_id]["replaced_by"] = new_key_id
        self._keys[new_key_id]["replaces"]    = old_key_id
        return new_record

    def revoke(self, key_id: str, reason: str) -> dict:
        if key_id not in self._keys:
            raise KeyError(f"key_id '{key_id}' not found")
        if not reason or not isinstance(reason, str):
            raise ValueError("revocation reason must be a non-empty string")
        current_status = self._keys[key_id]["status"]
        if current_status == self.STATUS_REVOKED:
            return {"status": "ALREADY_REVOKED", "key_id": key_id, "revoked_at": self._keys[key_id]["revoked_at"]}
        now = datetime.now(timezone.utc).isoformat()
        self._keys[key_id]["status"]            = self.STATUS_REVOKED
        self._keys[key_id]["revoked_at"]        = now
        self._keys[key_id]["revocation_reason"] = reason
        return {
            "status": "REVOKED", "key_id": key_id,
            "operator_id": self._keys[key_id]["operator_id"],
            "revoked_at": now, "revocation_reason": reason,
            "impact": "ALL signatures from this key are now rejected. Generate a new key and re-register immediately.",
        }

    def sign(self, key_id: str, payload: bytes) -> str:
        if not self.is_valid_for_signing(key_id):
            raise PermissionError(f"GAP-13: key '{key_id}' cannot sign — status is {self.get_status(key_id)}")
        private_key = self._keys[key_id]["_private_key"]
        return _sign(private_key, payload)

    def verify(self, key_id: str, payload: bytes, signature: str) -> tuple:
        if not self.is_valid_for_verification(key_id):
            return False, f"GAP-13: key '{key_id}' is {self.get_status(key_id)} — signature verification rejected. REVOKED keys cannot verify any signature."
        public_key = self._keys[key_id]["_public_key"]
        crypto_valid = _verify(public_key, signature, payload)
        if crypto_valid:
            return True, None
        return False, "signature verification failed — invalid signature"

    def export_public_record(self, key_id: str) -> dict:
        if key_id not in self._keys:
            raise KeyError(f"key_id '{key_id}' not found")
        record = self._keys[key_id]
        pub_bytes = record["_public_key"].public_bytes_raw()
        return {
            "key_id": key_id, "operator_id": record["operator_id"],
            "environment": record["environment"], "status": self.get_status(key_id),
            "created_at": record["created_at"], "expires_at": record["expires_at"],
            "rotated_at": record["rotated_at"], "revoked_at": record["revoked_at"],
            "revocation_reason": record["revocation_reason"],
            "replaced_by": record["replaced_by"], "replaces": record["replaces"],
            "public_key_hex": pub_bytes.hex(),
            "validity_months": record["validity_months"], "storage_spec": record["storage_spec"],
        }

# ═══════════════════ GAP‑11: OperatorRegistry ═══════════════════
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
        "objective_id": objective_id, "objective_description": objective_description,
        "constraint_set_hash": constraint_set_hash, "constraint_set_version": constraint_set_version,
        "committed_at": committed_at, "committed_by": committed_by,
    }
    commitment_id = _sha256(_canonical_json(preimage))
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
        "objective_id": commitment["objective_id"], "objective_description": ext.get("objective_description", ""),
        "constraint_set_hash": commitment["constraint_set_hash"],
        "constraint_set_version": ext.get("constraint_set_version", ""),
        "committed_at": commitment["committed_at"], "committed_by": commitment["committed_by"],
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
            "event": "COMMITMENT_ACTIVATED", "commitment_id": commitment["commitment_id"],
            "first_operator": commitment["committed_by"], "second_operator": second_operator_id,
            "activated_at": activated_at, "two_person_verified": True,
        }
        self._audit._append(activation_record, "commitment_id")
        return commitment

    def verify_commitment_status(self, commitment, operator_registry):
        try:
            if commitment.get("status") != "ACTIVE":
                return False, f"status is {commitment.get('status')}"
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
            first_op = commitment.get("committed_by")
            if not operator_registry.is_registered(first_op):
                return False, f"first operator '{first_op}' not registered"
            first_pub = operator_registry.get_public_key(first_op)
            if not _verify(first_pub, commitment["signature"], commitment["commitment_id"].encode("utf-8")):
                return False, "first signature invalid"
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
