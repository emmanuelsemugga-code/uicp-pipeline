#!/usr/bin/env python3
"""
tests/load_test.py — GAP‑17 Load Testing & Benchmarking

Sends batches of enforcement decisions through a mock gateway and
reports throughput, latency percentiles, and resource usage.
Does NOT require a live model or real API — self‑contained mock.
"""
import time, json, uuid, random, hashlib
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple


class MockGateway:
    """Minimal mock of Phase4EnforcementGateway for load testing."""
    def check_output(self, request: dict) -> dict:
        bindings = request.get("bindings", {})
        age = bindings.get("age", 0)
        violations = []
        if age < 18:
            violations.append({"constraint_identity": "AGE_CHECK", "canonical_form": "age >= 18", "actual_value_hash": "abc", "expected": "age >= 18"})
        status = "BLOCK" if violations else "ALLOW"
        return {"status": status, "violations": violations, "decision_id": hashlib.sha256(str(bindings).encode()).hexdigest()}


class LoadTester:
    def __init__(self, gateway, batch_sizes: List[int] = None):
        self.gateway = gateway
        self.batch_sizes = batch_sizes or [100, 1000, 10000]
        self._results: Dict[int, dict] = {}

    def run_all(self) -> dict:
        for size in self.batch_sizes:
            self._results[size] = self._run_batch(size)
        return self._build_report()

    def _run_batch(self, count: int) -> dict:
        latencies = []
        allows = 0
        blocks = 0
        start = time.time()
        for i in range(count):
            req_start = time.time()
            decision = self.gateway.check_output({
                "bindings": {"age": random.randint(10, 70), "risk": random.randint(1, 30)},
                "output_id": f"load-{i:06d}"
            })
            latencies.append((time.time() - req_start) * 1000)
            if decision["status"] == "ALLOW":
                allows += 1
            else:
                blocks += 1
        elapsed = time.time() - start
        sorted_lat = sorted(latencies)
        n = len(sorted_lat)
        return {
            "count": count,
            "total_sec": round(elapsed, 3),
            "throughput_per_sec": round(count / elapsed, 1),
            "latency_p50_ms": round(sorted_lat[n // 2], 3),
            "latency_p95_ms": round(sorted_lat[int(n * 0.95)], 3),
            "latency_p99_ms": round(sorted_lat[int(n * 0.99)], 3),
            "latency_max_ms": round(sorted_lat[-1], 3),
            "allows": allows,
            "blocks": blocks,
        }

    def _build_report(self) -> dict:
        return {
            "test_id": str(uuid.uuid4())[:8],
            "tested_at": datetime.now(timezone.utc).isoformat(),
            "batch_results": self._results,
            "summary": self._summary(),
        }

    def _summary(self) -> str:
        throughputs = [r["throughput_per_sec"] for r in self._results.values()]
        p99s = [r["latency_p99_ms"] for r in self._results.values()]
        return (
            f"Max throughput: {max(throughputs):.0f} decisions/sec. "
            f"Worst p99 latency: {max(p99s):.1f}ms. "
            f"Recommendation: {'Ready for production pilot' if max(p99s) < 100 else 'Optimize before pilot'}"
        )
