#!/usr/bin/env python3
"""
app/simulation_engine.py — GAP‑33 Constraint Simulation & Dry‑Run (FIXED v4)
Replays historical decisions against a new constraint, calculates impact,
assesses risk (GREEN/YELLOW/RED), and supports regression testing.
"""
import json, hashlib, time, uuid, re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple

# ── Data structures ─────────────────────────────────────────
class SimulationReport:
    def __init__(self, simulation_id: str = "", deployment_version: int = 0,
                 sample_size: int = 0, sampled_period: str = "",
                 summary: dict = None, decision_diff: list = None,
                 risk_level: str = "GREEN",
                 baseline_version: int = 0,
                 affected_constraints: list = None,
                 created_at: str = "", created_by: str = ""):
        self.simulation_id = simulation_id or str(uuid.uuid4())[:8]
        self.deployment_version = deployment_version
        self.sample_size = sample_size
        self.sampled_period = sampled_period
        self.summary = summary or {}
        self.decision_diff = decision_diff or []
        self.risk_level = risk_level
        self.baseline_version = baseline_version
        self.affected_constraints = affected_constraints or []
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.created_by = created_by
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "simulation_id": self.simulation_id,
            "deployment_version": self.deployment_version,
            "sample_size": self.sample_size,
            "sampled_period": self.sampled_period,
            "summary": self.summary,
            "decision_diff": self.decision_diff,
            "risk_level": self.risk_level,
            "baseline_version": self.baseline_version,
            "affected_constraints": self.affected_constraints,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "error": self.error,
        }


# ── Decision replay engine ──────────────────────────────────
class SimulationEngine:
    def __init__(self, audit_log, constraint_store, enforcement_gateway):
        self._audit_log = audit_log
        self._constraint_store = constraint_store
        self._gateway = enforcement_gateway

    def simulate(
        self,
        tenant_id: str,
        new_version: int,
        sample_size: int = 1000,
        include_diff: bool = True,
        diff_limit: int = 20,
        risk_threshold_green: float = 0.05,
        risk_threshold_red: float = 0.15,
        created_by: str = "",
    ) -> SimulationReport:
        """Run full simulation and return a report."""
        # 1. Load historical decisions
        historical = self._audit_log.get_decisions(tenant_id, limit=sample_size)
        if not historical:
            report = SimulationReport(
                deployment_version=new_version,
                sample_size=sample_size,
                created_by=created_by,
            )
            report.error = "No historical decisions found"
            return report

        # 2. Load new constraints
        new_constraints, new_version_actual = self._constraint_store.get_constraints(
            tenant_id, new_version
        )
        if not new_constraints or not new_constraints.get("canonical_constraints"):
            report = SimulationReport(
                deployment_version=new_version,
                sample_size=len(historical),
                created_by=created_by,
            )
            report.error = f"Constraint version {new_version} not found or empty"
            return report

        # ── FIX: apply constraints to the gateway BEFORE simulating ──
        if hasattr(self._gateway, "load_constraints"):
            self._gateway.load_constraints(new_constraints)
        elif hasattr(self._gateway, "_enforceable"):
            self._gateway._enforceable = new_constraints.get("canonical_constraints", [])
        elif hasattr(self._gateway, "_constraints"):
            self._gateway._constraints = new_constraints.get("canonical_constraints", [])

        # 3. Load baseline (current production) constraints
        baseline_version = self._get_current_version(tenant_id)

        # 4. Replay decisions with new constraints
        changes = []
        new_approvals = 0
        old_approvals = 0
        constraint_impact: Dict[str, int] = {}

        for decision in historical:
            bindings = decision.get("bindings", {})
            original_result = decision.get("result", decision.get("status", "UNKNOWN"))

            # Track old approval rate
            if original_result == "ALLOW":
                old_approvals += 1

            # Simulate with new constraints
            new_result = self._simulate_decision(bindings)

            # Track new approval rate
            if new_result == "ALLOW":
                new_approvals += 1

            # Record change
            if original_result != new_result:
                failed_constraints = self._find_failed_constraints(
                    bindings, new_constraints
                )
                changes.append({
                    "decision_id": decision.get("decision_id", ""),
                    "bindings": bindings,
                    "original": original_result,
                    "new": new_result,
                    "timestamp": decision.get("timestamp", ""),
                    "failed_constraints": failed_constraints,
                })
                for fc in failed_constraints:
                    constraint_impact[fc] = constraint_impact.get(fc, 0) + 1

        # 5. Analyze impact
        total = len(historical)
        changed = len(changes)
        allow_to_block = sum(1 for c in changes if c["original"] == "ALLOW" and c["new"] == "BLOCK")
        block_to_allow = sum(1 for c in changes if c["original"] == "BLOCK" and c["new"] == "ALLOW")
        approval_rate_old = old_approvals / total if total else 0
        approval_rate_new = new_approvals / total if total else 0
        approval_rate_change_pct = (
            (approval_rate_new - approval_rate_old) / approval_rate_old * 100
        ) if approval_rate_old > 0 else 0

        summary = {
            "total_decisions_tested": total,
            "decisions_changed": changed,
            "percent_changed": round(changed / total * 100, 2) if total else 0,
            "allow_to_block": allow_to_block,
            "block_to_allow": block_to_allow,
            "approval_rate_old": round(approval_rate_old, 4),
            "approval_rate_new": round(approval_rate_new, 4),
            "approval_rate_change_pct": round(approval_rate_change_pct, 2),
        }

        # 6. Assess risk
        risk_level = self._assess_risk(
            abs(approval_rate_change_pct), risk_threshold_green, risk_threshold_red
        )

        # 7. Build affected constraints list
        affected = [
            {"name": name, "decisions_affected": count}
            for name, count in sorted(
                constraint_impact.items(), key=lambda x: x[1], reverse=True
            )
        ]

        # 8. Build report
        report = SimulationReport(
            simulation_id=str(uuid.uuid4())[:8],
            deployment_version=new_version_actual,
            sample_size=total,
            sampled_period=self._get_period(historical),
            summary=summary,
            decision_diff=changes[:diff_limit] if include_diff else [],
            risk_level=risk_level,
            baseline_version=baseline_version,
            affected_constraints=affected,
            created_by=created_by,
        )
        return report

    def regression_test(
        self,
        simulation_report: SimulationReport,
        deployment_id: str,
        hours: int = 1,
    ) -> dict:
        """Compare simulation predictions to actual deployment results."""
        actual_metrics = self._audit_log.get_deployment_metrics(
            deployment_id, hours
        )
        if not actual_metrics:
            return {"error": "No deployment metrics found", "accuracy": "UNKNOWN"}

        predicted_rate = simulation_report.summary.get("approval_rate_new", 0)
        actual_rate = actual_metrics.get("approval_rate", 0)
        diff = abs(actual_rate - predicted_rate) if predicted_rate else 0

        accuracy = "HIGH"
        if diff >= 0.05:
            accuracy = "LOW"
        elif diff >= 0.02:
            accuracy = "MEDIUM"

        return {
            "predicted_approval_rate": round(predicted_rate, 4),
            "actual_approval_rate": round(actual_rate, 4),
            "difference": round(diff, 4),
            "accuracy": accuracy,
            "prediction_trustworthy": diff < 0.05,
        }

    # ── Helpers ──────────────────────────────────────────────
    def _get_current_version(self, tenant_id: str) -> int:
        active = self._constraint_store.get_active_version(tenant_id)
        if active:
            return active.get("version", 1)
        return 1

    def _simulate_decision(self, bindings: dict) -> str:
        """Evaluate constraints against bindings. Returns ALLOW or BLOCK."""
        result = self._gateway.check_output({
            "bindings": bindings,
            "output_id": "simulation",
        })
        return result.get("status", "UNKNOWN")

    def _find_failed_constraints(
        self, bindings: dict, constraints: dict
    ) -> List[str]:
        """Return list of constraint names that would fail for these bindings."""
        failed = []
        for c in constraints.get("canonical_constraints", []):
            cf = c.get("canonical_form", "")
            if not cf:
                continue
            if self._evaluate_single(cf, bindings) is False:
                failed.append(c.get("identity_string", cf))
        return failed

    def _evaluate_single(self, canonical_form: str, bindings: dict) -> Optional[bool]:
        """Evaluate a single constraint. Returns True/False/None."""
        m = re.match(
            r'^\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?)\s*$',
            canonical_form,
        )
        if not m:
            return None
        var, op, val_str = m.group(1), m.group(2), m.group(3)
        if var not in bindings:
            return None
        try:
            val = float(val_str)
            binding = float(bindings[var])
        except (ValueError, TypeError):
            return None
        if op == ">=": return binding >= val
        if op == "<=": return binding <= val
        if op == ">":  return binding > val
        if op == "<":  return binding < val
        if op == "==": return binding == val
        if op == "!=": return binding != val
        return None

    @staticmethod
    def _assess_risk(change_pct: float, green: float, red: float) -> str:
        if change_pct < green:
            return "GREEN"
        if change_pct < red:
            return "YELLOW"
        return "RED"

    @staticmethod
    def _get_period(historical: list) -> str:
        if not historical:
            return "unknown"
        first = historical[-1].get("timestamp", "")
        last = historical[0].get("timestamp", "")
        return f"{first} to {last}"


# ── Stub classes for Colab testing ──────────────────────────
class _StubAuditLog:
    def __init__(self, decisions: list = None):
        self._decisions = decisions or []

    def get_decisions(self, tenant_id: str, limit: int = 1000) -> list:
        return [d for d in self._decisions if d.get("tenant_id") == tenant_id][:limit]

    def get_deployment_metrics(self, deployment_id: str, hours: int = 1) -> dict:
        return {"approval_rate": 0.90}


class _StubConstraintStore:
    def __init__(self, constraints_by_version: dict = None, active_version: int = 1):
        self._constraints = constraints_by_version or {}
        self._active_version = active_version

    def get_constraints(self, tenant_id: str, version: int) -> tuple:
        content = self._constraints.get(version, {"canonical_constraints": []})
        return content, version

    def get_active_version(self, tenant_id: str) -> dict:
        return {"version": self._active_version}


class _StubGateway:
    def __init__(self):
        self._constraints = []

    def load_constraints(self, constraints: dict):
        """Called by SimulationEngine before each simulation run."""
        self._constraints = constraints.get("canonical_constraints", [])

    def check_output(self, request: dict) -> dict:
        bindings = request.get("bindings", {})
        violations = []
        for c in self._constraints:
            cf = c.get("canonical_form", "")
            m = re.match(
                r'^\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?)\s*$', cf
            )
            if not m:
                continue
            var, op, val_str = m.group(1), m.group(2), m.group(3)
            if var not in bindings:
                continue
            try:
                val = float(val_str)
                binding = float(bindings[var])
            except (ValueError, TypeError):
                continue
            passed = False
            if op == ">=": passed = binding >= val
            elif op == "<=": passed = binding <= val
            elif op == ">": passed = binding > val
            elif op == "<": passed = binding < val
            elif op == "==": passed = binding == val
            elif op == "!=": passed = binding != val
            if not passed:
                violations.append({
                    "constraint_identity": c.get("identity_string", cf),
                    "canonical_form": cf,
                    "actual_value": binding,
                    "expected": cf,
                })
        status = "BLOCK" if violations else "ALLOW"
        return {
            "status": status,
            "violations": violations,
            "decision_id": hashlib.sha256(
                (status + str(violations)).encode()
            ).hexdigest(),
        }
