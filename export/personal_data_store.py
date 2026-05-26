#!/usr/bin/env python3
"""
export/personal_data_store.py — GAP‑44 Off‑Chain Personal Data Store

Stores personal data (actual binding values) outside the cryptographic
audit chain. Enables GDPR Article 17 right of erasure without breaking
chain integrity.
"""

import hashlib, json, os, tempfile
from datetime import datetime, timezone


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


# ── Built‑in test suite ──────────────────────────────────────────
def _run_gap44_tests():
    passed = failed = 0

    def chk(label, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  GAP‑44 | {label}")
        else:
            failed += 1
            print(f"  FAIL  GAP‑44 | {label}" +
                  (f" — {detail}" if detail else ""))

    print("\n=== GAP‑44 GDPR Erasure Architecture Tests ===\n")

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        store = PersonalDataStore(store_path=tmp_path)

        # 1. Write / read
        rid = store.write("dec-001", "age", 16)
        chk("write() returns 64‑char record_id",
            isinstance(rid, str) and len(rid) == 64)
        rec = store.read(rid)
        chk("read() returns actual_value=16",
            rec is not None and rec["actual_value"] == 16)
        chk("read() returns variable_name='age'",
            rec["variable_name"] == "age")
        chk("read() returns erased=False before erasure",
            rec["erased"] == False)

        # 2. Hashes
        h = PersonalDataStore.compute_hash(16)
        chk("compute_hash returns 64‑char hex", len(h) == 64)
        chk("compute_hash is deterministic",
            PersonalDataStore.compute_hash(16) == h)
        chk("different values → different hashes",
            PersonalDataStore.compute_hash(16) !=
            PersonalDataStore.compute_hash(17))

        # 3. Chain pointer verification
        valid, _ = store.verify_chain_pointer(rid, h)
        chk("verify_chain_pointer passes for correct hash", valid)
        valid_w, _ = store.verify_chain_pointer(rid, "a" * 64)
        chk("verify_chain_pointer fails for wrong hash", not valid_w)
        valid_nf, _ = store.verify_chain_pointer("nonexistent", h)
        chk("verify_chain_pointer fails for unknown record_id", not valid_nf)

        # 4. Erasure
        erasure = store.erase(rid)
        chk("erase() returns ERASED", erasure["status"] == "ERASED")
        chk("erase() confirms GDPR Article 17",
            erasure.get("gdpr_article") == "Article 17 — Right to Erasure")
        chk("erase() confirms chain_impact is NONE",
            erasure.get("chain_impact") == "NONE — chain integrity preserved")

        # 5. Post‑erasure
        rec2 = store.read(rid)
        chk("read() after erasure → erased=True", rec2["erased"] == True)
        chk("read() after erasure → actual_value=None",
            rec2["actual_value"] is None)
        double = store.erase(rid)
        chk("double erase() → ALREADY_ERASED",
            double["status"] == "ALREADY_ERASED")
        nf = store.erase("nonexistent-record-id")
        chk("erase() on unknown record → NOT_FOUND",
            nf["status"] == "NOT_FOUND")

        # 6. Chain pointer after erasure
        valid_e, reason_e = store.verify_chain_pointer(rid, h)
        chk("verify_chain_pointer after erasure returns False with reason",
            not valid_e and "erased" in reason_e.lower())

        # 7. Erase by decision
        store.write("dec-002", "age",  35)
        store.write("dec-002", "risk", 8)
        results = store.erase_by_decision("dec-002")
        chk("erase_by_decision() erases all records for decision",
            len(results) == 2 and all(r["status"] == "ERASED"
                                      for r in results))
        nf_d = store.erase_by_decision("dec-999")
        chk("erase_by_decision() → NOT_FOUND for unknown decision",
            nf_d[0]["status"] == "NOT_FOUND")

        # 8. Erasure log
        log = store.export_erasure_log()
        chk("erasure log contains erased records", len(log) >= 3)
        chk("erasure log never contains actual_value",
            all("actual_value" not in e for e in log))

        # 9. Stats
        stats = store.stats()
        chk("stats() returns total_records", "total_records" in stats)
        chk("stats() erased_records matches erasure log length",
            stats["erased_records"] == len(log))

        # 10. Record ID determinism
        r1 = PersonalDataStore.compute_record_id("dec-001", "age")
        r2 = PersonalDataStore.compute_record_id("dec-001", "age")
        r3 = PersonalDataStore.compute_record_id("dec-001", "risk")
        chk("compute_record_id is deterministic", r1 == r2)
        chk("different variables → different record_ids", r1 != r3)

    finally:
        os.unlink(tmp_path)

    total = passed + failed
    print(f"\n=== GAP‑44 Results: {passed}/{total} passed ===")
    if failed > 0:
        print("FAIL — do not commit")
    else:
        print("ALL GAP‑44 TESTS PASSED — ready for PR")
    return passed, failed


if __name__ == "__main__":
    _run_gap44_tests()
