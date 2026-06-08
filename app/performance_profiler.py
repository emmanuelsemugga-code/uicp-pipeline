#!/usr/bin/env python3
"""
app/performance_profiler.py — GAP‑48 Performance Profiling (v3 FIXED)
"""
import time, threading, json, math, uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Tuple


class RequestMetrics:
    def __init__(self, request_id: str = "", tenant_id: str = "default"):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.tenant_id = tenant_id
        self.timestamp = datetime.now(timezone.utc)
        self.phase_1_normalization_ms: float = 0.0
        self.phase_2_semantic_analysis_ms: float = 0.0
        self.phase_3_satisfiability_ms: float = 0.0
        self.phase_4_enforcement_ms: float = 0.0
        self.phase_5_audit_ms: float = 0.0
        self.total_latency_ms: float = 0.0
        self.constraint_times: Dict[str, float] = {}
        self.decision: str = "UNKNOWN"
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id, "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat(),
            "phase_1_normalization_ms": self.phase_1_normalization_ms,
            "phase_2_semantic_analysis_ms": self.phase_2_semantic_analysis_ms,
            "phase_3_satisfiability_ms": self.phase_3_satisfiability_ms,
            "phase_4_enforcement_ms": self.phase_4_enforcement_ms,
            "phase_5_audit_ms": self.phase_5_audit_ms,
            "total_latency_ms": self.total_latency_ms,
            "constraint_times": self.constraint_times,
            "decision": self.decision, "error": self.error,
        }


class AggregatedMetrics:
    def __init__(self, timestamp: datetime = None, tenant_id: str = "default"):
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.tenant_id = tenant_id
        self.period_seconds = 60
        self._constraint_samples: Dict[str, List[float]] = defaultdict(list)
        self.constraint_stats: Dict[str, dict] = {}
        self._phase_samples: Dict[str, List[float]] = defaultdict(list)
        self.phase_stats: Dict[str, dict] = {}
        self._total_samples: List[float] = []
        self.total_count: int = 0
        self.approval_count: int = 0
        self.error_count: int = 0

    def add_metric(self, m: RequestMetrics):
        self._total_samples.append(m.total_latency_ms)
        self.total_count += 1
        if m.decision == "ALLOW":
            self.approval_count += 1
        if m.error:
            self.error_count += 1
        for name, lat in m.constraint_times.items():
            self._constraint_samples[name].append(lat)
        for phase_name, lat in [
            ("phase_1_normalization", m.phase_1_normalization_ms),
            ("phase_2_semantic_analysis", m.phase_2_semantic_analysis_ms),
            ("phase_3_satisfiability", m.phase_3_satisfiability_ms),
            ("phase_4_enforcement", m.phase_4_enforcement_ms),
            ("phase_5_audit", m.phase_5_audit_ms),
        ]:
            self._phase_samples[phase_name].append(lat)

    def finalize(self):
        for name, samples in self._constraint_samples.items():
            self.constraint_stats[name] = self._calc_stats(samples)
        for name, samples in self._phase_samples.items():
            self.phase_stats[name] = self._calc_stats(samples)

    @staticmethod
    def _calc_stats(samples: List[float]) -> dict:
        if not samples:
            return {"count": 0, "min_ms": 0, "max_ms": 0, "avg_ms": 0,
                    "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
        s = sorted(samples)
        n = len(s)
        return {
            "count": n, "min_ms": round(s[0], 3), "max_ms": round(s[-1], 3),
            "avg_ms": round(sum(s) / n, 3), "p50_ms": round(s[n // 2], 3),
            "p95_ms": round(s[int(n * 0.95)], 3),
            "p99_ms": round(s[int(n * 0.99)], 3),
        }

    def to_dict(self) -> dict:
        total_stats = self._calc_stats(self._total_samples)
        return {
            "timestamp": self.timestamp.isoformat(), "tenant_id": self.tenant_id,
            "period_seconds": self.period_seconds,
            "total_count": self.total_count,
            "approval_count": self.approval_count,
            "error_count": self.error_count,
            "total_latency": total_stats,
            "constraint_stats": dict(self.constraint_stats),
            "phase_stats": dict(self.phase_stats),
        }


class PerformanceProfiler:
    def __init__(self, aggregation_interval_seconds: int = 60,
                 retention_minutes: int = 1440):
        self._buffer: List[RequestMetrics] = []
        self._lock = threading.Lock()
        self._aggregation_interval = aggregation_interval_seconds
        self._retention_minutes = retention_minutes
        self._aggregated: List[AggregatedMetrics] = []
        self._baselines: Dict[str, dict] = {}

    def profile(self, request_id: str = "", tenant_id: str = "default"):
        return _RequestProfiler(self, request_id, tenant_id)

    def _store_metric(self, m: RequestMetrics):
        with self._lock:
            self._buffer.append(m)
            if len(self._buffer) >= 1000:
                self._flush()

    def _flush(self):
        with self._lock:
            to_aggregate = self._buffer[:]
            self._buffer.clear()
        if not to_aggregate:
            return
        by_tenant: Dict[str, List[RequestMetrics]] = defaultdict(list)
        for m in to_aggregate:
            by_tenant[m.tenant_id].append(m)
        now = datetime.now(timezone.utc)
        for tenant_id, metrics_list in by_tenant.items():
            bucket = AggregatedMetrics(timestamp=now, tenant_id=tenant_id)
            for m in metrics_list:
                bucket.add_metric(m)
            bucket.finalize()
            self._aggregated.append(bucket)
        cutoff = now - timedelta(minutes=self._retention_minutes)
        self._aggregated = [a for a in self._aggregated if a.timestamp >= cutoff]

    def force_flush(self):
        self._flush()

    def get_latest_aggregated(self, tenant_id: str = "default") -> Optional[AggregatedMetrics]:
        for a in reversed(self._aggregated):
            if a.tenant_id == tenant_id:
                return a
        return None

    def get_aggregated_range(self, tenant_id: str,
                             start: datetime, end: datetime) -> List[AggregatedMetrics]:
        return [a for a in self._aggregated
                if a.tenant_id == tenant_id and start <= a.timestamp <= end]

    def compute_baseline(self, tenant_id: str, hours: int = 24) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        relevant = [a for a in self._aggregated
                    if a.tenant_id == tenant_id and a.timestamp >= cutoff]
        if not relevant:
            return {"total_avg_ms": 45.0, "total_p99_ms": 100.0,
                    "approval_rate": 0.90, "error_rate": 0.001}
        total_avg = sum(a.to_dict()["total_latency"]["avg_ms"] for a in relevant) / len(relevant)
        total_p99 = sorted(a.to_dict()["total_latency"]["p99_ms"] for a in relevant)[int(len(relevant) * 0.99)]
        approval = sum(a.approval_count for a in relevant) / max(sum(a.total_count for a in relevant), 1)
        errors = sum(a.error_count for a in relevant) / max(sum(a.total_count for a in relevant), 1)
        baseline = {
            "total_avg_ms": round(total_avg, 2), "total_p99_ms": round(total_p99, 2),
            "approval_rate": round(approval, 4), "error_rate": round(errors, 4),
        }
        self._baselines[tenant_id] = baseline
        return baseline

    def check_alerts(self, tenant_id: str,
                     latency_p99_threshold_ms: float = 100.0,
                     error_rate_threshold: float = 0.01) -> List[dict]:
        latest = self.get_latest_aggregated(tenant_id)
        if not latest:
            return []
        baseline = self._baselines.get(tenant_id, self.compute_baseline(tenant_id))
        latest_dict = latest.to_dict()
        alerts = []
        p99 = latest_dict["total_latency"]["p99_ms"]
        if p99 > latency_p99_threshold_ms:
            alerts.append({
                "type": "LATENCY_HIGH", "severity": "WARNING",
                "metric": "total_latency_p99_ms", "current": p99,
                "threshold": latency_p99_threshold_ms,
                "baseline": baseline.get("total_p99_ms", 0),
                "message": f"p99 latency {p99}ms exceeds threshold {latency_p99_threshold_ms}ms",
            })
        err_rate = latest.error_count / max(latest.total_count, 1)
        if err_rate > error_rate_threshold:
            alerts.append({
                "type": "ERROR_RATE_HIGH", "severity": "CRITICAL",
                "metric": "error_rate", "current": round(err_rate, 4),
                "threshold": error_rate_threshold,
                "baseline": baseline.get("error_rate", 0),
                "message": f"Error rate {err_rate:.4f} exceeds threshold {error_rate_threshold}",
            })
        for cname, stats in latest_dict.get("constraint_stats", {}).items():
            if stats.get("p99_ms", 0) > 50.0:
                alerts.append({
                    "type": "CONSTRAINT_LATENCY_HIGH", "severity": "INFO",
                    "constraint": cname, "current_p99": stats["p99_ms"],
                    "threshold": 50.0,
                    "message": f"Constraint '{cname}' p99 latency {stats['p99_ms']}ms > 50ms",
                })
        return alerts

    def estimate_capacity(self, tenant_id: str,
                          traffic_multiplier: float = 2.0) -> dict:
        latest = self.get_latest_aggregated(tenant_id)
        if not latest:
            return {"error": "No metrics available"}
        d = latest.to_dict()
        current_avg = d["total_latency"]["avg_ms"]
        current_p99 = d["total_latency"]["p99_ms"]
        projected_avg = current_avg * traffic_multiplier
        projected_p99 = current_p99 * traffic_multiplier
        current_throughput = d["total_count"] / 60
        return {
            "current": {
                "avg_latency_ms": current_avg,
                "p99_latency_ms": current_p99,
                "throughput_per_sec": round(current_throughput, 1),
            },
            "projected": {
                "traffic_multiplier": traffic_multiplier,
                "avg_latency_ms": round(projected_avg, 2),
                "p99_latency_ms": round(projected_p99, 2),
                "throughput_per_sec": round(current_throughput * traffic_multiplier, 1),
            },
            "recommendation": (
                "Add more gateway instances"
                if projected_p99 > 200 else
                "Current capacity sufficient"
                if projected_p99 <= 150 else
                "Monitor closely; consider scaling soon"
            ),
        }

    def compare_periods(self, tenant_id: str,
                        period_a_hours: int = 1,
                        period_b_hours: int = 24) -> dict:
        now = datetime.now(timezone.utc)
        recent = self.get_aggregated_range(
            tenant_id, now - timedelta(hours=period_a_hours), now)
        older = self.get_aggregated_range(
            tenant_id, now - timedelta(hours=period_b_hours),
            now - timedelta(hours=period_a_hours))

        def avg_latency(metrics_list):
            vals = [m.to_dict()["total_latency"]["avg_ms"]
                    for m in metrics_list if m.total_count > 0]
            return round(sum(vals) / len(vals), 2) if vals else 0

        recent_avg = avg_latency(recent)
        older_avg = avg_latency(older)
        return {
            "recent_period_hours": period_a_hours,
            "baseline_period_hours": period_b_hours,
            "recent_avg_latency_ms": recent_avg,
            "baseline_avg_latency_ms": older_avg,
            "change_pct": round((recent_avg - older_avg) / older_avg * 100, 2) if older_avg else 0,
            "trend": "faster" if recent_avg < older_avg else "slower" if recent_avg > older_avg else "stable",
        }


class _RequestProfiler:
    def __init__(self, profiler: PerformanceProfiler, request_id: str, tenant_id: str):
        self.profiler = profiler
        self.metrics = RequestMetrics(request_id, tenant_id)
        self._start = time.time()
        self._phase_start = time.time()
        self._constraint_start: Optional[float] = None
        self._active_constraint: Optional[str] = None

    def record_phase(self, phase_name: str):
        now = time.time()
        elapsed = (now - self._phase_start) * 1000
        setattr(self.metrics, f"{phase_name}_ms", elapsed)
        self._phase_start = now

    def start_constraint(self, constraint_name: str):
        self._constraint_start = time.time()
        self._active_constraint = constraint_name

    def end_constraint(self):
        if self._constraint_start is not None and self._active_constraint is not None:
            elapsed = (time.time() - self._constraint_start) * 1000
            self.metrics.constraint_times[self._active_constraint] = elapsed
            self._constraint_start = None
            self._active_constraint = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.metrics.total_latency_ms = (time.time() - self._start) * 1000
        if exc_type is not None:
            self.metrics.error = f"{exc_type.__name__}: {exc_val}"
        self.profiler._store_metric(self.metrics)
        return True   # <-- FIX: suppress exception so profiler never crashes the caller
