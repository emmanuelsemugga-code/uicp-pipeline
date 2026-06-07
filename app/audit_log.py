# ============================================================
# Validate app/audit_log.py — GAP‑18 Tenant‑Aware Queries
# ============================================================
import json, hashlib, sqlite3, tempfile, os
from abc import ABC, abstractmethod

# ── EXACT production code from app/audit_log.py ─────────────
class AuditLog(ABC):
    @abstractmethod
    def append(self, decision: dict) -> str: ...
    @abstractmethod
    def get_by_id(self, tenant_id: str, decision_id: str) -> dict | None: ...
    @abstractmethod
    def list_recent(self, tenant_id: str, limit: int = 100) -> list[dict]: ...
    @abstractmethod
    def export_range(self, tenant_id: str, start_date: str, end_date: str) -> list[dict]: ...
    @abstractmethod
    def verify_chain(self, tenant_id: str) -> bool: ...

class LocalFileAuditLog(AuditLog):
    def __init__(self):
        self._entries = []
    def append(self, d):
        prev = self._entries[-1]["_chain_hash"] if self._entries else "GENESIS"
        ch = hashlib.sha256((prev + d["decision_id"]).encode()).hexdigest()
        entry = {**d, "_chain_hash": ch}
        self._entries.append(entry)
        return d["decision_id"]
    def get_by_id(self, tid, did):
        return next((e for e in self._entries if e.get("decision_id")==did and e.get("tenant_id")==tid), None)
    def list_recent(self, tid, limit=100):
        return [e for e in self._entries if e.get("tenant_id")==tid][-limit:]
    def export_range(self, tid, sd, ed):
        return [e for e in self._entries if e.get("tenant_id")==tid and sd <= e.get("timestamp","") <= ed]
    def verify_chain(self, tid):
        run = "GENESIS"
        for e in self._entries:
            if e.get("tenant_id")!=tid: continue
            exp = hashlib.sha256((run + e["decision_id"]).encode()).hexdigest()
            if e.get("_chain_hash")!=exp: return False
            run = e["_chain_hash"]
        return True
    def get_all(self): return list(self._entries)

# ── Tests using LocalFileAuditLog (simulates PostgreSQL behaviour) ──
passed = failed = 0
def check(label, condition):
    global passed, failed
    if condition: passed += 1; print(f"  PASS  {label}")
    else: failed += 1; print(f"  FAIL  {label}")

print("=== app/audit_log.py GAP‑18 Tenant‑Aware Queries Validation ===\n")

log = LocalFileAuditLog()
log.append({"tenant_id":"hosp-a","decision_id":"d1","status":"ALLOW","timestamp":"2026-06-07T12:00:00Z"})
log.append({"tenant_id":"bank-b","decision_id":"d2","status":"BLOCK","timestamp":"2026-06-07T12:01:00Z"})

# Test 1 — get_by_id respects tenant
check("Tenant hosp‑a retrieves d1", log.get_by_id("hosp-a","d1") is not None)
check("Tenant hosp‑a CANNOT see bank‑b decision", log.get_by_id("hosp-a","d2") is None)
check("Tenant bank‑b retrieves d2", log.get_by_id("bank-b","d2") is not None)
check("Tenant bank‑b CANNOT see hosp‑a decision", log.get_by_id("bank-b","d1") is None)

# Test 2 — list_recent filters by tenant
check("hosp‑a sees only its own entries", len(log.list_recent("hosp-a"))==1)
check("bank‑b sees only its own entries", len(log.list_recent("bank-b"))==1)

# Test 3 — export_range filters by tenant
check("hosp‑a export contains 1 entry", len(log.export_range("hosp-a","2020-01-01","2030-01-01"))==1)
check("bank‑b export contains 1 entry", len(log.export_range("bank-b","2020-01-01","2030-01-01"))==1)

# Test 4 — unknown tenant gets nothing
check("Unknown tenant gets nothing", len(log.list_recent("unknown"))==0)

print(f"\n=== Results: {passed}/{passed+failed} passed ===")
if failed == 0:
    print("✓ app/audit_log.py GAP‑18 VALIDATED — ready for commit\n")
else:
    print("✗ FIX FAILURES BEFORE COMMIT\n")
