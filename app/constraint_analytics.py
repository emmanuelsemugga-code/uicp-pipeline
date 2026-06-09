#!/usr/bin/env python3
"""
app/constraint_analytics.py — GAP‑34 Constraint Analytics & Usage Reporting (FIXED v2)
"""
import json, time, uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


class ConstraintUsageRecord:
    def __init__(self, constraint_name: str, decision: str,
                 latency_ms: float = 0.0):
        self.constraint_name = constraint_name
        self.decision = decision
        self.latency_ms = latency_ms
        self.timestamp = datetime.now(timezone.utc)


class UsageReport:
    def __init__(self, tenant_id: str = "",
                 period_start: str = "", period_end: str = ""):
        self.tenant_id = tenant_id
        self.period_start = period_start
        self.period_end = period_end
        self.total_evaluations: int = 0
        self.total_allows: int = 0
        self.total_blocks: int = 0
        self.constraint_stats: Dict[str, dict] = {}
        self.most_violated: List[Tuple[str, int]] = []
        self.never_triggered: List[str] = []
        self.approval_rate_trend: List[dict] = []
        self.anomalies: List[dict] = []

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_evaluations": self.total_evaluations,
            "total_allows": self.total_allows,
            "total_blocks": self.total_blocks,
            "constraint_stats": self.constraint_stats,
            "most_violated": [{"name": n, "count": c} for n, c in self.most_violated],
            "never_triggered": self.never_triggered,
            "approval_rate_trend": self.approval_rate_trend,
            "anomalies": self.anomalies,
        }


class ConstraintAnalytics:
    def __init__(self):
        self._records: Dict[str, Dict[str, List[ConstraintUsageRecord]]] = defaultdict(
            lambda: defaultdict(list))
        self._hourly_buckets: Dict[str, Dict[str, List[int]]] = defaultdict(
            lambda: defaultdict(list))

    def record_evaluation(self, tenant_id: str, constraint_name: str,
                          decision: str, latency_ms: float = 0.0):
        rec = ConstraintUsageRecord(constraint_name, decision, latency_ms)
        self._records[tenant_id][constraint_name].append(rec)
        hour_key = rec.timestamp.strftime("%Y-%m-%dT%H:00+00:00")
        self._hourly_buckets[tenant_id][hour_key].append(
            1 if decision == "ALLOW" else 0
        )

    def get_constraint_stats(self, tenant_id: str,
                             constraint_name: str) -> dict:
        records = self._records.get(tenant_id, {}).get(constraint_name, [])
        if not records:
            return {"evaluations": 0, "allows": 0, "blocks": 0,
                    "avg_latency_ms": 0, "last_evaluated": None}
        evaluations = len(records)
        allows = sum(1 for r in records if r.decision == "ALLOW")
        blocks = evaluations - allows
        avg_latency = sum(r.latency_ms for r in records) / evaluations if evaluations else 0
        last = max(r.timestamp for r in records).isoformat()
        return {
            "evaluations": evaluations,
            "allows": allows,
            "blocks": blocks,
            "avg_latency_ms": round(avg_latency, 2),
            "last_evaluated": last,
        }

    def generate_report(self, tenant_id: str,
                        hours: int = 24) -> UsageReport:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        report = UsageReport(
            tenant_id=tenant_id,
            period_start=cutoff.isoformat(),
            period_end=now.isoformat(),
        )
        all_names = self._records.get(tenant_id, {})
        if not all_names:
            return report

        total_evaluations = 0
        total_allows = 0
        total_blocks = 0

        for cname, records in all_names.items():
            recent = [r for r in records if r.timestamp >= cutoff]
            if not recent:
                continue
            evals = len(recent)
            allows = sum(1 for r in recent if r.decision == "ALLOW")
            blocks = evals - allows
            total_evaluations += evals
            total_allows += allows
            total_blocks += blocks
            report.constraint_stats[cname] = {
                "evaluations": evals,
                "allows": allows,
                "blocks": blocks,
                "block_rate": round(blocks / evals, 4) if evals else 0,
                "avg_latency_ms": round(
                    sum(r.latency_ms for r in recent) / evals, 2
                ) if evals else 0,
            }

        report.total_evaluations = total_evaluations
        report.total_allows = total_allows
        report.total_blocks = total_blocks

        violated = [(n, s["blocks"]) for n, s in report.constraint_stats.items()
                    if s["blocks"] > 0]
        violated.sort(key=lambda x: x[1], reverse=True)
        report.most_violated = violated[:10]

        active = set(report.constraint_stats.keys())
        report.never_triggered = sorted(set(all_names.keys()) - active)

        hourly = self._hourly_buckets.get(tenant_id, {})
        for hour_key in sorted(hourly.keys()):
            hour_dt = datetime.fromisoformat(hour_key)
            if hour_dt >= cutoff:
                decisions = hourly[hour_key]
                if decisions:
                    report.approval_rate_trend.append({
                        "hour": hour_key,
                        "total": len(decisions),
                        "approval_rate": round(
                            sum(decisions) / len(decisions), 4
                        ),
                    })

        for entry in report.approval_rate_trend:
            if entry["approval_rate"] < 0.70 and entry["total"] >= 10:
                report.anomalies.append({
                    "hour": entry["hour"],
                    "type": "LOW_APPROVAL_RATE",
                    "approval_rate": entry["approval_rate"],
                    "total_decisions": entry["total"],
                    "message": f"Approval rate dropped to {entry['approval_rate']:.1%}",
                })

        return report

    def get_most_violated(self, tenant_id: str,
                          top_n: int = 10) -> List[Tuple[str, int]]:
        stats = self._records.get(tenant_id, {})
        counts = []
        for cname, records in stats.items():
            blocks = sum(1 for r in records if r.decision == "BLOCK")
            if blocks > 0:
                counts.append((cname, blocks))
        counts.sort(key=lambda x: x[1], reverse=True)
        return counts[:top_n]

    def get_never_triggered(self, tenant_id: str,
                            registered_constraints: List[str]) -> List[str]:
        triggered = set(self._records.get(tenant_id, {}).keys())
        return sorted(set(registered_constraints) - triggered)
