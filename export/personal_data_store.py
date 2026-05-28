#!/usr/bin/env python3
"""
export/personal_data_store.py — GAP‑44 + GAP‑45
Off‑chain personal data store with AES‑256‑GCM encryption,
role‑based access control, and access event logging.
"""
import hashlib, json, os
from datetime import datetime, timezone

# ═══════════════════ GAP‑44 PersonalDataStore ═══════════════════
class PersonalDataStore:
    """Off‑chain store for personal binding values."""

    def __init__(self, store_path: str = "personal_data_store.json"):
        self._path    = store_path
        self._records = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        with open(self._path, 'w') as f:
            json.dump(self._records, f, indent=2)

    @staticmethod
    def compute_hash(actual_value: int) -> str:
        return hashlib.sha256(
            str(actual_value).encode('utf-8')
        ).hexdigest()

    @staticmethod
    def compute_record_id(decision_id: str, variable_name: str) -> str:
        return hashlib.sha256(
            f"{decision_id}:{variable_name}".encode('utf-8')
        ).hexdigest()

    def write(self, decision_id: str, variable_name: str,
              actual_value: int) -> str:
        record_id = self.compute_record_id(decision_id, variable_name)
        self._records[record_id] = {
            "record_id":     record_id,
            "decision_id":   decision_id,
            "variable_name": variable_name,
            "actual_value":  actual_value,
            "value_hash":    self.compute_hash(actual_value),
            "written_at":    datetime.now(timezone.utc).isoformat(),
            "erased":        False,
            "erased_at":     None,
        }
        self._save()
        return record_id

    def read(self, record_id: str) -> dict | None:
        record = self._records.get(record_id)
        if record is None:
            return None
        if record["erased"]:
            return {
                "record_id":     record_id,
                "decision_id":   record["decision_id"],
                "variable_name": record["variable_name"],
                "actual_value":  None,
                "value_hash":    record["value_hash"],
                "erased":        True,
                "erased_at":     record["erased_at"],
            }
        return dict(record)

    def erase(self, record_id: str) -> dict:
        if record_id not in self._records:
            return {"status": "NOT_FOUND", "record_id": record_id,
                    "message": "No record found for this record_id"}
        record = self._records[record_id]
        if record["erased"]:
            return {"status": "ALREADY_ERASED", "record_id": record_id,
                    "erased_at": record["erased_at"],
                    "message": "Data was previously erased"}
        erased_at = datetime.now(timezone.utc).isoformat()
        self._records[record_id]["actual_value"] = None
        self._records[record_id]["erased"]       = True
        self._records[record_id]["erased_at"]    = erased_at
        self._save()
        return {
            "status": "ERASED", "record_id": record_id,
            "decision_id": record["decision_id"],
            "variable_name": record["variable_name"],
            "value_hash": record["value_hash"],
            "erased_at": erased_at,
            "chain_impact": "NONE — chain integrity preserved",
            "gdpr_article": "Article 17 — Right to Erasure",
        }

    def erase_by_decision(self, decision_id: str) -> list:
        results = []
        for record_id, record in self._records.items():
            if record["decision_id"] == decision_id:
                results.append(self.erase(record_id))
        return results if results else [{
            "status": "NOT_FOUND", "decision_id": decision_id,
            "message": "No personal data found for this decision_id",
        }]

    def verify_chain_pointer(self, record_id: str,
                             stored_hash: str) -> tuple:
        record = self._records.get(record_id)
        if record is None:
            return False, "record not found in personal data store"
        if record["erased"]:
            return False, ("data has been erased per GDPR Article 17 — "
                           "value_hash preserved for chain consistency check")
        recomputed = self.compute_hash(record["actual_value"])
        if recomputed == stored_hash:
            return True, None
        return False, (f"hash mismatch — store may be tampered. "
                       f"stored_hash={stored_hash[:16]}… "
                       f"computed={recomputed[:16]}…")

    def export_erasure_log(self) -> list:
        return [
            {
                "record_id":     r["record_id"],
                "decision_id":   r["decision_id"],
                "variable_name": r["variable_name"],
                "value_hash":    r["value_hash"],
                "erased_at":     r["erased_at"],
            }
            for r in self._records.values()
            if r["erased"]
        ]

    def stats(self) -> dict:
        total  = len(self._records)
        erased = sum(1 for r in self._records.values() if r["erased"])
        return {
            "total_records":  total,
            "active_records": total - erased,
            "erased_records": erased,
            "store_path":     self._path,
        }


# ═══════════════════ GAP‑45 EncryptedPersonalDataStore ═══════════════════
class EncryptedPersonalDataStore(PersonalDataStore):
    """
    GAP‑45 PATCH: AES‑256‑GCM encrypted wrapper for PersonalDataStore.
    """

    ROLE_GATEWAY  = "gateway"
    ROLE_AUDITOR  = "auditor"
    ROLE_OPERATOR = "operator"

    def __init__(self, store_path: str, encryption_key: bytes,
                 access_log_path: str = None,
                 role: str = ROLE_GATEWAY):
        if len(encryption_key) != 32:
            raise ValueError("encryption_key must be 32 bytes")
        if role not in (self.ROLE_GATEWAY, self.ROLE_AUDITOR, self.ROLE_OPERATOR):
            raise ValueError("role must be gateway, auditor, or operator")

        self._encryption_key  = encryption_key
        self._access_log_path = access_log_path
        self._role            = role
        self._access_events   = self._load_access_log()
        self._path    = store_path
        self._records = self._load()

    @staticmethod
    def generate_key() -> bytes:
        return os.urandom(32)

    def _load(self) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path, 'rb') as f:
                ciphertext = f.read()
            if len(ciphertext) < 12:
                return {}
            nonce      = ciphertext[:12]
            ciphertext = ciphertext[12:]
            aesgcm     = AESGCM(self._encryption_key)
            plaintext  = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(plaintext.decode('utf-8'))
        except Exception:
            self._log_access_event("LOAD_FAILURE", "SYSTEM", "decryption failed")
            return {}

    def _save(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        plaintext  = json.dumps(self._records).encode('utf-8')
        nonce      = os.urandom(12)
        aesgcm     = AESGCM(self._encryption_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        os.makedirs(os.path.dirname(self._path) if os.path.dirname(self._path) else '.', exist_ok=True)
        with open(self._path, 'wb') as f:
            f.write(nonce + ciphertext)

    def _load_access_log(self) -> list:
        if not self._access_log_path or not os.path.exists(self._access_log_path):
            return []
        try:
            with open(self._access_log_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def _save_access_log(self):
        if not self._access_log_path:
            return
        os.makedirs(os.path.dirname(self._access_log_path) if os.path.dirname(self._access_log_path) else '.', exist_ok=True)
        with open(self._access_log_path, 'w') as f:
            json.dump(self._access_events, f, indent=2)

    def _log_access_event(self, operation: str, record_id: str, detail: str = "") -> dict:
        event = {
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "role":       self._role,
            "operation":  operation,
            "record_id":  record_id[:16] + "…" if len(record_id) > 16 else record_id,
            "detail":     detail,
        }
        self._access_events.append(event)
        self._save_access_log()
        return event

    def write(self, decision_id: str, variable_name: str, actual_value: int) -> str:
        if self._role in (self.ROLE_AUDITOR, self.ROLE_OPERATOR):
            raise PermissionError(f"GAP-45: {self._role} role cannot write to PersonalDataStore")
        rid = super().write(decision_id, variable_name, actual_value)
        self._log_access_event("WRITE", rid, f"variable={variable_name}")
        return rid

    def read(self, record_id: str) -> dict | None:
        if self._role == self.ROLE_OPERATOR:
            raise PermissionError("GAP-45: operator role cannot read PersonalDataStore directly")
        result = super().read(record_id)
        self._log_access_event("READ", record_id, "erased" if result and result.get("erased") else "active")
        return result

    def erase(self, record_id: str) -> dict:
        if self._role != self.ROLE_GATEWAY:
            raise PermissionError(f"GAP-45: only gateway role can erase. Current role: {self._role}")
        result = super().erase(record_id)
        self._log_access_event("ERASE", record_id, result.get("status", "UNKNOWN"))
        return result

    def export_access_log(self) -> list:
        return list(self._access_events)

    def stats(self) -> dict:
        base = super().stats()
        base["encrypted"]        = True
        base["role"]             = self._role
        base["access_events"]    = len(self._access_events)
        base["access_log_path"]  = self._access_log_path
        return base
        # ── GAP‑44 tests ───────────────────────────────────────────────────
def _run_gap44_tests():
    import tempfile, os
    passed = failed = 0
    def chk(label, condition, detail=""):
        nonlocal passed, failed
        if condition: passed += 1; print(f"  PASS  GAP-44 | {label}")
        else: failed += 1; print(f"  FAIL  GAP-44 | {label}" + (f" — {detail}" if detail else ""))
    print("\n=== GAP-44 GDPR Erasure Architecture Tests ===\n")
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name
    try:
        store = PersonalDataStore(store_path=tmp_path)
        rid = store.write("dec-001", "age", 16)
        chk("write() returns 64-char record_id", isinstance(rid, str) and len(rid)==64)
        rec = store.read(rid)
        chk("read() returns actual_value=16", rec is not None and rec["actual_value"]==16)
        h = PersonalDataStore.compute_hash(16)
        chk("compute_hash returns 64-char hex", len(h)==64)
        chk("compute_hash is deterministic", PersonalDataStore.compute_hash(16)==h)
        valid, _ = store.verify_chain_pointer(rid, h)
        chk("verify_chain_pointer passes for correct hash", valid)
        erasure = store.erase(rid)
        chk("erase() returns ERASED", erasure["status"]=="ERASED")
        chk("erase() confirms GDPR Article 17", erasure.get("gdpr_article")=="Article 17 — Right to Erasure")
        rec2 = store.read(rid)
        chk("read() after erasure → erased=True", rec2["erased"]==True)
        chk("read() after erasure → actual_value=None", rec2["actual_value"] is None)
    finally:
        os.unlink(tmp_path)
    total = passed + failed
    print(f"\n=== GAP-44 Results: {passed}/{total} passed ===")
    if failed > 0: print("FAIL — do not commit")
    else: print("ALL GAP-44 TESTS PASSED — ready for PR")
    return passed, failed


# ── GAP‑45 tests ───────────────────────────────────────────────────
def _run_gap45_tests():
    import tempfile, os
    passed = failed = 0
    def chk(label, condition, detail=""):
        nonlocal passed, failed
        if condition: passed += 1; print(f"  PASS  GAP-45 | {label}")
        else: failed += 1; print(f"  FAIL  GAP-45 | {label}" + (f" — {detail}" if detail else ""))
    print("\n=== GAP-45 Access Control & Encryption Tests ===\n")
    with tempfile.NamedTemporaryFile(suffix='.enc', delete=False) as f:
        enc_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        log_path = f.name
    try:
        key = EncryptedPersonalDataStore.generate_key()
        chk("generate_key returns 32 bytes", len(key)==32)
        chk("generate_key is random — two keys differ", EncryptedPersonalDataStore.generate_key()!=key)
        try: EncryptedPersonalDataStore(enc_path, b"tooshort", log_path, "gateway"); chk("Short key raises ValueError", False)
        except ValueError: chk("Short key raises ValueError", True)
        try: EncryptedPersonalDataStore(enc_path, key, log_path, "superuser"); chk("Invalid role raises ValueError", False)
        except ValueError: chk("Invalid role raises ValueError", True)

        gateway = EncryptedPersonalDataStore(enc_path, key, log_path, "gateway")
        rid = gateway.write("dec-001", "age", 16)
        chk("Gateway write() succeeds", isinstance(rid, str) and len(rid)==64)
        rec = gateway.read(rid)
        chk("Gateway read() returns correct value", rec is not None and rec["actual_value"]==16)

        with open(enc_path, 'rb') as f:
            raw_bytes = f.read()
        chk("Encrypted file is binary not plain JSON", not raw_bytes.startswith(b'{'))
        chk("Encrypted file does not contain raw value as string", b'"actual_value": 16' not in raw_bytes and b'actual_value' not in raw_bytes)

        gateway2 = EncryptedPersonalDataStore(enc_path, key, log_path, "gateway")
        rec2 = gateway2.read(rid)
        chk("Decryption with correct key returns value", rec2 is not None and rec2["actual_value"]==16)

        wrong_key = EncryptedPersonalDataStore.generate_key()
        gateway_wrong = EncryptedPersonalDataStore(enc_path, wrong_key, log_path, "gateway")
        wrong_record = gateway_wrong.read(rid)
        chk("Wrong key cannot read records", wrong_record is None)

        auditor = EncryptedPersonalDataStore(enc_path, key, log_path, "auditor")
        chk("Auditor read() succeeds", auditor.read(rid) is not None)
        try: auditor.write("dec-002", "risk", 8); chk("Auditor write() raises PermissionError", False)
        except PermissionError: chk("Auditor write() raises PermissionError", True)
        try: auditor.erase(rid); chk("Auditor erase() raises PermissionError", False)
        except PermissionError: chk("Auditor erase() raises PermissionError", True)

        operator = EncryptedPersonalDataStore(enc_path, key, log_path, "operator")
        try: operator.write("dec-003", "income", 50000); chk("Operator write() raises PermissionError", False)
        except PermissionError: chk("Operator write() raises PermissionError", True)
        try: operator.read(rid); chk("Operator read() raises PermissionError", False)
        except PermissionError: chk("Operator read() raises PermissionError", True)
        try: operator.erase(rid); chk("Operator erase() raises PermissionError", False)
        except PermissionError: chk("Operator erase() raises PermissionError", True)

        events = gateway.export_access_log()
        chk("Access log contains events", len(events)>0)
        chk("Access log events have timestamp", all("timestamp" in e for e in events))
        chk("Access log events have role", all("role" in e for e in events))
        chk("Access log events have operation", all("operation" in e for e in events))

        gateway3 = EncryptedPersonalDataStore(enc_path, key, log_path, "gateway")
        events3 = gateway3.export_access_log()
        chk("Access log persists across store instances", len(events3)>0)

        stats = gateway.stats()
        chk("stats() shows encrypted=True", stats.get("encrypted")==True)
        chk("stats() shows current role", stats.get("role")=="gateway")
        chk("stats() shows access event count", "access_events" in stats)

        erasure = gateway.erase(rid)
        chk("Encrypted store erasure returns ERASED", erasure.get("status")=="ERASED")
        erased = gateway.read(rid)
        chk("Erased record has actual_value=None after encrypted erasure", erased is not None and erased["actual_value"] is None)

    finally:
        for path in [enc_path, log_path]:
            try: os.unlink(path)
            except Exception: pass

    total = passed + failed
    print(f"\n=== GAP-45 Results: {passed}/{total} passed ===")
    if failed > 0: print("FAIL — do not commit")
    else: print("ALL GAP-45 TESTS PASSED — ready for PR")
    return passed, failed


# ── MAIN RUNNER ────────────────────────────────────────────────────
if __name__ == "__main__":
    g44_pass, g44_fail = _run_gap44_tests()
    g45_pass, g45_fail = _run_gap45_tests()
    total_pass = g44_pass + g45_pass
    total_fail = g44_fail + g45_fail
    print("\n" + "="*60)
    print(f"COMBINED RESULTS: {total_pass} passed, {total_fail} failed")
    if total_fail == 0:
        print("  ✓ ALL TESTS PASS — GAP‑44 + GAP‑45 are ALIGNED.\n")
    else:
        print(f"  ✗ {total_fail} FAILURE(S) — Investigate.\n")
        
