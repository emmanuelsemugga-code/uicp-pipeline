#!/usr/bin/env python3
"""
app/constraint_sla.py — GAP‑25 Constraint Performance SLA & Latency Guarantees (FIXED)
"""
import time, json, uuid, threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


# ── SLA data structures ─────────────────────────────────────
class SLABudget:
    def __init__(self, constraint_name: str, max_latency_ms: float = 50.0,
                 max_violations_per_window: int = 10,
                 window_seconds: int = 300):
        self.constraint_name = constraint_name
        self.max_latency_ms = max_latency_ms
        self.max_violations_per_window = max_violations_per_window
        self.window_seconds = window_seconds
        self.budget_remaining = max_violations_per_window
        self.window_start = datetime.now(timezone.utc)
        self.total_violations = 0
        self.total_evaluations = 0
        self.last_violation_at: Optional[str] = None
        self.status = "HEALTHY"

    def record_evaluation(self, latency_ms: float):
        self.total_evaluations += 1
        now = datetime.now(timezone.utc)

        if (now - self.window_start).total_seconds() > self.window_seconds:
            self.budget_remaining = self.max_violations_per_window
            self.window_start = now

        if latency_ms > self.max_latency_ms:
            self.budget_remaining -= 1
            self.total_violations += 1
            self.last_violation_at = now.isoformat()

        if self.budget_remaining <= 0:
            self.status = "EXCEEDED"
        elif self.budget_remaining < self.max_violations_per_window * 0.5:
            self.status = "WARNING"
        else:
            self.status = "HEALTHY"

    def is_exceeded(self) -> bool:
        return self.status == "EXCEEDED"

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "max_latency_ms": self.max_latency_ms,
            "budget_remaining": self.budget_remaining,
            "max_violations_per_window": self.max_violations_per_window,
            "window_seconds": self.window_seconds,
            "total_violations": self.total_violations,
            "total_evaluations": self.total_evaluations,
            "status": self.status,
            "last_violation_at": self.last_violation_at,
        }


class SLAReport:
    def __init__(self, tenant_id: str = ""):
        self.tenant_id = tenant_id
        self.budgets: Dict[str, SLABudget] = {}
        self.global_violations: int = 0
        self.degraded_constraints: List[str] = []
        self.overall_status = "HEALTHY"
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "budgets": {k: v.to_dict() for k, v in self.budgets.items()},
            "global_violations": self.global_violations,
            "degraded_constraints": self.degraded_constraints,
            "overall_status": self.overall_status,
            "created_at": self.created_at,
        }


# ── SLA Manager ─────────────────────────────────────────────
class SLAManager:
    def __init__(self, alert_manager=None):
        self._budgets: Dict[str, Dict[str, SLABudget]] = defaultdict(dict)
        self._alert_manager = alert_manager
        self._degraded_constraints: Dict[str, List[str]] = defaultdict(list)

    def register_constraint(self, tenant_id: str, constraint_name: str,
                            max_latency_ms: float = 50.0,
                            max_violations_per_window: int = 10,
                            window_seconds: int = 300):
        self._budgets[tenant_id][constraint_name] = SLABudget(
            constraint_name=constraint_name,
            max_latency_ms=max_latency_ms,
            max_violations_per_window=max_violations_per_window,
            window_seconds=window_seconds,
        )

    def record_evaluation(self, tenant_id: str, constraint_name: str,
                          latency_ms: float):
        budget = self._budgets.get(tenant_id, {}).get(constraint_name)
        if budget is None:
            return

        previous_status = budget.status
        budget.record_evaluation(latency_ms)

        if budget.status == "EXCEEDED" and previous_status != "EXCEEDED":
            if constraint_name not in self._degraded_constraints[tenant_id]:
                self._degraded_constraints[tenant_id].append(constraint_name)

        # FIX: remove from degraded list on recovery (budget reset or window roll)
        if budget.status != "EXCEEDED" and constraint_name in self._degraded_constraints.get(tenant_id, []):
            self._degraded_constraints[tenant_id].remove(constraint_name)

    def is_constraint_degraded(self, tenant_id: str, constraint_name: str) -> bool:
        budget = self._budgets.get(tenant_id, {}).get(constraint_name)
        return budget.is_exceeded() if budget else False

    def get_degraded_constraints(self, tenant_id: str) -> List[str]:
        return self._degraded_constraints.get(tenant_id, [])

    def generate_report(self, tenant_id: str) -> SLAReport:
        report = SLAReport(tenant_id=tenant_id)
        budgets = self._budgets.get(tenant_id, {})
        report.budgets = {k: v for k, v in budgets.items()}
        report.global_violations = sum(b.total_violations for b in budgets.values())
        report.degraded_constraints = self._degraded_constraints.get(tenant_id, [])
        if report.degraded_constraints:
            report.overall_status = "DEGRADED"
        elif any(b.status == "WARNING" for b in budgets.values()):
            report.overall_status = "WARNING"
        else:
            report.overall_status = "HEALTHY"
        return report

    def get_budget(self, tenant_id: str, constraint_name: str) -> Optional[SLABudget]:
        return self._budgets.get(tenant_id, {}).get(constraint_name)

    def reset_budget(self, tenant_id: str, constraint_name: str):
        budget = self._budgets.get(tenant_id, {}).get(constraint_name)
        if budget:
            budget.budget_remaining = budget.max_violations_per_window
            budget.window_start = datetime.now(timezone.utc)
            budget.status = "HEALTHY"
        # FIX: also remove from degraded list
        if constraint_name in self._degraded_constraints.get(tenant_id, []):
            self._degraded_constraints[tenant_id].remove(constraint_name)


# ── Circuit breaker ──────────────────────────────────────────
class CircuitBreaker:
    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, sla_manager: SLAManager,
                 open_timeout_seconds: int = 60):
        self._sla = sla_manager
        self._open_timeout = open_timeout_seconds
        self._open_since: Dict[str, Dict[str, datetime]] = defaultdict(dict)

    def should_execute(self, tenant_id: str, constraint_name: str) -> bool:
        state = self._get_state(tenant_id, constraint_name)
        if state == self.STATE_CLOSED:
            return True
        if state == self.STATE_OPEN:
            opened_at = self._open_since.get(tenant_id, {}).get(constraint_name)
            if opened_at:
                elapsed = (datetime.now(timezone.utc) - opened_at).total_seconds()
                if elapsed >= self._open_timeout:
                    self._set_state(tenant_id, constraint_name, self.STATE_HALF_OPEN)
                    return True
            return False
        return True

    def record_success(self, tenant_id: str, constraint_name: str):
        current = self._get_state(tenant_id, constraint_name)
        if current == self.STATE_HALF_OPEN:
            self._set_state(tenant_id, constraint_name, self.STATE_CLOSED)
            if tenant_id in self._open_since:
                self._open_since[tenant_id].pop(constraint_name, None)

    def record_failure(self, tenant_id: str, constraint_name: str):
        current = self._get_state(tenant_id, constraint_name)
        if current in (self.STATE_CLOSED, self.STATE_HALF_OPEN):
            self._set_state(tenant_id, constraint_name, self.STATE_OPEN)
            self._open_since[tenant_id][constraint_name] = datetime.now(timezone.utc)

    def _get_state(self, tenant_id: str, constraint_name: str) -> str:
        if constraint_name in self._open_since.get(tenant_id, {}):
            # Check if timeout has elapsed
            opened_at = self._open_since[tenant_id][constraint_name]
            elapsed = (datetime.now(timezone.utc) - opened_at).total_seconds()
            if elapsed >= self._open_timeout:
                return self.STATE_HALF_OPEN
            return self.STATE_OPEN
        return self.STATE_CLOSED

    def _set_state(self, tenant_id: str, constraint_name: str, state: str):
        if state == self.STATE_OPEN:
            self._open_since[tenant_id][constraint_name] = datetime.now(timezone.utc)
        elif state == self.STATE_CLOSED:
            if tenant_id in self._open_since:
                self._open_since[tenant_id].pop(constraint_name, None)
