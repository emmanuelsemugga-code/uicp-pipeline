#!/usr/bin/env python3
"""
app/complexity_limits.py — GAP‑26 Constraint Complexity Limits & Circuit‑Breaker
Enforces limits on constraint complexity (depth, operators, variables) and
circuit‑breaks evaluation when limits are exceeded.
"""
import time, re, uuid, threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict


# ── Complexity profile ──────────────────────────────────────
class ComplexityProfile:
    def __init__(self, constraint_name: str, canonical_form: str):
        self.constraint_name = constraint_name
        self.canonical_form = canonical_form
        self.depth: int = 0
        self.operator_count: int = 0
        self.variable_count: int = 0
        self.or_clauses: int = 0
        self.and_clauses: int = 0
        self.total_nodes: int = 0
        self._analyze()

    def _analyze(self):
        cf = self.canonical_form
        # Count operators
        self.operator_count = len(re.findall(r'[<>=!+\-*/()]', cf))
        # Count variables
        tokens = re.findall(r'[A-Za-z_]\w*', cf)
        keywords = {"AND", "OR", "NOT", "IF", "THEN", "ELSE"}
        self.variable_count = len(set(t for t in tokens if t.upper() not in keywords))
        # Count OR/AND clauses
        self.or_clauses = len(re.findall(r'\bOR\b', cf, re.IGNORECASE))
        self.and_clauses = len(re.findall(r'\bAND\b', cf, re.IGNORECASE))
        # Estimate depth (parentheses nesting)
        depth = 0
        max_depth = 0
        for ch in cf:
            if ch == '(':
                depth += 1
                max_depth = max(max_depth, depth)
            elif ch == ')':
                depth -= 1
        self.depth = max_depth
        # Total nodes (operators + variables + constants)
        constants = len(re.findall(r'-?\d+\.?\d*', cf))
        self.total_nodes = self.operator_count + self.variable_count + constants

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "depth": self.depth,
            "operator_count": self.operator_count,
            "variable_count": self.variable_count,
            "or_clauses": self.or_clauses,
            "and_clauses": self.and_clauses,
            "total_nodes": self.total_nodes,
        }


# ── Complexity limits ───────────────────────────────────────
class ComplexityLimits:
    def __init__(self, max_depth: int = 10, max_operators: int = 50,
                 max_variables: int = 20, max_or_clauses: int = 10,
                 max_and_clauses: int = 20, max_nodes: int = 256,
                 max_evaluation_time_ms: float = 1000.0):
        self.max_depth = max_depth
        self.max_operators = max_operators
        self.max_variables = max_variables
        self.max_or_clauses = max_or_clauses
        self.max_and_clauses = max_and_clauses
        self.max_nodes = max_nodes
        self.max_evaluation_time_ms = max_evaluation_time_ms

    def to_dict(self) -> dict:
        return {
            "max_depth": self.max_depth,
            "max_operators": self.max_operators,
            "max_variables": self.max_variables,
            "max_or_clauses": self.max_or_clauses,
            "max_and_clauses": self.max_and_clauses,
            "max_nodes": self.max_nodes,
            "max_evaluation_time_ms": self.max_evaluation_time_ms,
        }


class ComplexityViolation:
    def __init__(self, field: str, limit: int, actual: int,
                 constraint_name: str = ""):
        self.field = field
        self.limit = limit
        self.actual = actual
        self.constraint_name = constraint_name
        self.message = f"{field}: {actual} exceeds limit {limit}"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "limit": self.limit,
            "actual": self.actual,
            "constraint_name": self.constraint_name,
            "message": self.message,
        }


# ── Evaluation timeout guard ─────────────────────────────────
class EvaluationTimeoutError(Exception):
    def __init__(self, constraint_name: str, elapsed_ms: float, limit_ms: float):
        self.constraint_name = constraint_name
        self.elapsed_ms = elapsed_ms
        self.limit_ms = limit_ms
        super().__init__(f"Evaluation of {constraint_name} timed out: "
                         f"{elapsed_ms:.1f}ms > {limit_ms}ms")


class TimeoutGuard:
    def __init__(self, timeout_ms: float, constraint_name: str):
        self.timeout_ms = timeout_ms
        self.constraint_name = constraint_name
        self.start_time: Optional[float] = None
        self.timed_out = False

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            elapsed = (time.time() - self.start_time) * 1000
            if elapsed > self.timeout_ms:
                self.timed_out = True
                raise EvaluationTimeoutError(
                    self.constraint_name, elapsed, self.timeout_ms
                )
        return False


# ── Complexity Checker ──────────────────────────────────────
class ComplexityChecker:
    def __init__(self, limits: ComplexityLimits = None):
        self.limits = limits or ComplexityLimits()

    def check(self, constraint_name: str, canonical_form: str) -> List[ComplexityViolation]:
        profile = ComplexityProfile(constraint_name, canonical_form)
        violations: List[ComplexityViolation] = []

        checks = [
            ("depth", profile.depth, self.limits.max_depth),
            ("operators", profile.operator_count, self.limits.max_operators),
            ("variables", profile.variable_count, self.limits.max_variables),
            ("or_clauses", profile.or_clauses, self.limits.max_or_clauses),
            ("and_clauses", profile.and_clauses, self.limits.max_and_clauses),
            ("total_nodes", profile.total_nodes, self.limits.max_nodes),
        ]

        for field, actual, limit in checks:
            if actual > limit:
                violations.append(ComplexityViolation(
                    field=field, limit=limit, actual=actual,
                    constraint_name=constraint_name,
                ))

        return violations

    def is_within_limits(self, constraint_name: str, canonical_form: str) -> bool:
        return len(self.check(constraint_name, canonical_form)) == 0


# ── Circuit breaker for complexity ─────────────────────────
class ComplexityCircuitBreaker:
    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, max_violations: int = 5,
                 window_seconds: int = 300,
                 open_timeout_seconds: int = 120):
        self.max_violations = max_violations
        self.window_seconds = window_seconds
        self.open_timeout_seconds = open_timeout_seconds
        self._violations: Dict[str, List[datetime]] = defaultdict(list)
        self._open_since: Dict[str, datetime] = {}
        self._state: Dict[str, str] = defaultdict(lambda: self.STATE_CLOSED)

    def record_violation(self, constraint_name: str):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._violations[constraint_name] = [
            v for v in self._violations.get(constraint_name, []) if v >= cutoff
        ]
        self._violations[constraint_name].append(now)

        if len(self._violations[constraint_name]) >= self.max_violations:
            self._state[constraint_name] = self.STATE_OPEN
            self._open_since[constraint_name] = now

    def should_execute(self, constraint_name: str) -> bool:
        state = self._state.get(constraint_name, self.STATE_CLOSED)
        if state == self.STATE_CLOSED:
            return True
        if state == self.STATE_OPEN:
            opened_at = self._open_since.get(constraint_name)
            if opened_at:
                elapsed = (datetime.now(timezone.utc) - opened_at).total_seconds()
                if elapsed >= self.open_timeout_seconds:
                    self._state[constraint_name] = self.STATE_HALF_OPEN
                    return True
            return False
        # HALF_OPEN: allow one probe
        return True

    def record_success(self, constraint_name: str):
        if self._state.get(constraint_name) == self.STATE_HALF_OPEN:
            self._state[constraint_name] = self.STATE_CLOSED
            self._violations[constraint_name] = []
            self._open_since.pop(constraint_name, None)

    def record_failure(self, constraint_name: str):
        state = self._state.get(constraint_name, self.STATE_CLOSED)
        if state in (self.STATE_CLOSED, self.STATE_HALF_OPEN):
            self._state[constraint_name] = self.STATE_OPEN
            self._open_since[constraint_name] = datetime.now(timezone.utc)

    def get_state(self, constraint_name: str) -> str:
        return self._state.get(constraint_name, self.STATE_CLOSED)

    def reset(self, constraint_name: str):
        self._violations[constraint_name] = []
        self._open_since.pop(constraint_name, None)
        self._state[constraint_name] = self.STATE_CLOSED
