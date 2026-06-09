#!/usr/bin/env python3
"""
app/constraint_staleness.py — GAP‑48 Constraint Staleness Detection
Flags constraints that have not been reviewed within a configurable window.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional


class StalenessCheck:
    def __init__(self, constraint_name: str, last_reviewed: str,
                 staleness_months: int, status: str, reason: str = ""):
        self.constraint_name = constraint_name
        self.last_reviewed = last_reviewed
        self.staleness_months = staleness_months
        self.status = status            # "FRESH", "STALE", "CRITICAL"
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "last_reviewed": self.last_reviewed,
            "staleness_months": self.staleness_months,
            "status": self.status,
            "reason": self.reason,
        }


class ConstraintStalenessDetector:
    """
    Detects constraints that have not been reviewed within a configurable window.

    Default thresholds:
      - FRESH: reviewed within 6 months
      - STALE: not reviewed in 6‑12 months — needs review
      - CRITICAL: not reviewed in over 12 months — compliance risk
    """

    def __init__(self, fresh_months: int = 6, critical_months: int = 12):
        self.fresh_months = fresh_months
        self.critical_months = critical_months

    def check_constraint(self, name: str, last_reviewed: str) -> StalenessCheck:
        """Check a single constraint for staleness."""
        try:
            reviewed_dt = datetime.fromisoformat(last_reviewed)
        except (ValueError, TypeError):
            return StalenessCheck(
                name, last_reviewed, 0, "UNKNOWN",
                "Invalid or missing last_reviewed date"
            )

        now = datetime.now(timezone.utc)
        if reviewed_dt.tzinfo is None:
            reviewed_dt = reviewed_dt.replace(tzinfo=timezone.utc)

        diff = now - reviewed_dt
        months = diff.days // 30

        if months < self.fresh_months:
            return StalenessCheck(name, last_reviewed, months, "FRESH")
        elif months < self.critical_months:
            return StalenessCheck(
                name, last_reviewed, months, "STALE",
                f"Last reviewed {months} months ago — needs review"
            )
        else:
            return StalenessCheck(
                name, last_reviewed, months, "CRITICAL",
                f"Last reviewed {months} months ago — compliance risk"
            )

    def check_all(self, constraints: List[dict]) -> List[StalenessCheck]:
        """Check all constraints in a set. Each dict must have identity_string and last_reviewed."""
        results = []
        for c in constraints:
            name = c.get("identity_string", c.get("name", "UNKNOWN"))
            last = c.get("last_reviewed", c.get("reviewed_at", ""))
            results.append(self.check_constraint(name, last))
        return results

    def generate_report(self, constraints: List[dict]) -> dict:
        """Generate a full staleness report."""
        checks = self.check_all(constraints)
        fresh = [c for c in checks if c.status == "FRESH"]
        stale = [c for c in checks if c.status == "STALE"]
        critical = [c for c in checks if c.status == "CRITICAL"]
        return {
            "total_constraints": len(constraints),
            "fresh": len(fresh),
            "stale": len(stale),
            "critical": len(critical),
            "fresh_constraints": [c.to_dict() for c in fresh],
            "stale_constraints": [c.to_dict() for c in stale],
            "critical_constraints": [c.to_dict() for c in critical],
            "recommendation": self._recommendation(stale, critical),
        }

    @staticmethod
    def _recommendation(stale: list, critical: list) -> str:
        if critical:
            return (
                f"CRITICAL: {len(critical)} constraint(s) not reviewed in over "
                f"12 months. Immediate review required for compliance."
            )
        if stale:
            return (
                f"WARNING: {len(stale)} constraint(s) not reviewed in 6‑12 months. "
                f"Schedule review within 30 days."
            )
        return "All constraints reviewed within 6 months."
