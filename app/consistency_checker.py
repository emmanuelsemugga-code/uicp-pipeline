#!/usr/bin/env python3
"""
app/consistency_checker.py — GAP‑24 Cross‑Constraint Consistency Checking
Detects contradictions, redundancy, semantic conflicts, and unsatisfiable sets.
Generates test cases and coverage reports for constraint operators.
"""
import json, re, itertools, math
from typing import List, Dict, Optional, Tuple, Set, Union

# ── Data structures ─────────────────────────────────────────
class ConstraintExpression:
    def __init__(self, variable: str = "", operator: str = "",
                 value: Union[int, float] = None,
                 expr_type: str = "SIMPLE",
                 left=None, right=None,
                 original: str = ""):
        self.variable = variable
        self.operator = operator
        self.value = value
        self.type = expr_type        # "SIMPLE" or "AND"
        self.left = left
        self.right = right
        self.original = original

    def __repr__(self):
        if self.type == "SIMPLE":
            return f"({self.variable} {self.operator} {self.value})"
        return f"({self.left} AND {self.right})"


class ConsistencyReport:
    def __init__(self, constraints: List[dict] = None):
        self.constraints = constraints or []
        self.issues: List[dict] = []
        self.risk_level = "GREEN"
        self.satisfiable = True
        self.coverage: dict = {}
        self.test_cases: List[dict] = []

    def add_issue(self, issue_type: str, constraint_a: str, constraint_b: str,
                  reason: str, severity: str = "WARNING"):
        self.issues.append({
            "type": issue_type,
            "constraint_a": constraint_a,
            "constraint_b": constraint_b,
            "reason": reason,
            "severity": severity,
        })
        if severity == "CRITICAL" and self.risk_level != "RED":
            self.risk_level = "RED"
        elif severity == "WARNING" and self.risk_level == "GREEN":
            self.risk_level = "YELLOW"

    def to_dict(self) -> dict:
        return {
            "total_constraints": len(self.constraints),
            "issues_found": len(self.issues),
            "risk_level": self.risk_level,
            "satisfiable": self.satisfiable,
            "issues": self.issues,
            "coverage": self.coverage,
            "test_cases": self.test_cases,
            "recommendation": self._recommendation(),
        }

    def _recommendation(self) -> str:
        if self.risk_level == "RED":
            return "CRITICAL: Fix constraint conflicts before deployment"
        if self.risk_level == "YELLOW":
            return "WARNING: Review constraints and deploy with caution"
        return "OK: Constraints are consistent"


# ── Constraint parser ───────────────────────────────────────
_SIMPLE_RE = re.compile(
    r'^\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?)\s*$'
)
_AND_RE = re.compile(r'\s+AND\s+', re.IGNORECASE)


class ConstraintParser:
    @staticmethod
    def parse(canonical_form: str) -> Optional[ConstraintExpression]:
        """Parse a canonical_form string into a ConstraintExpression."""
        if not canonical_form or not isinstance(canonical_form, str):
            return None
        m = _SIMPLE_RE.match(canonical_form)
        if m:
            var, op, val_str = m.group(1), m.group(2), m.group(3)
            try:
                val = float(val_str)
                if val == int(val):
                    val = int(val)
            except ValueError:
                return None
            return ConstraintExpression(
                variable=var, operator=op, value=val,
                expr_type="SIMPLE", original=canonical_form,
            )
        parts = _AND_RE.split(canonical_form)
        if len(parts) >= 2:
            parsed = [ConstraintParser.parse(p.strip()) for p in parts]
            parsed = [p for p in parsed if p is not None]
            if len(parsed) >= 2:
                result = parsed[0]
                for p in parsed[1:]:
                    result = ConstraintExpression(
                        expr_type="AND", left=result, right=p,
                        original=canonical_form,
                    )
                return result
        return None

    @staticmethod
    def extract_variables(expr: ConstraintExpression) -> Set[str]:
        """Return all variable names in an expression tree."""
        if expr.type == "SIMPLE":
            return {expr.variable}
        if expr.type == "AND":
            left_vars = ConstraintParser.extract_variables(expr.left) if expr.left else set()
            right_vars = ConstraintParser.extract_variables(expr.right) if expr.right else set()
            return left_vars | right_vars
        return set()

    @staticmethod
    def extract_bounds(expr: ConstraintExpression, var: str) -> Dict[str, Optional[float]]:
        bounds: Dict[str, Optional[float]] = {"min": None, "max": None}
        def _walk(node):
            if node is None:
                return
            if node.type == "SIMPLE" and node.variable == var:
                op, val = node.operator, node.value
                if op in (">=", ">"):
                    effective = val if op == ">=" else val
                    bounds["min"] = effective if bounds["min"] is None else max(bounds["min"], effective)
                elif op in ("<=", "<"):
                    effective = val if op == "<=" else val
                    bounds["max"] = effective if bounds["max"] is None else min(bounds["max"], effective)
                elif op == "==":
                    bounds["min"] = bounds["max"] = val
            elif node.type == "AND":
                _walk(node.left)
                _walk(node.right)
        _walk(expr)
        return bounds

    @staticmethod
    def extract_all_bounds(constraints: List[dict]) -> Dict[str, Dict[str, Optional[float]]]:
        all_bounds: Dict[str, Dict[str, Optional[float]]] = {}
        for c in constraints:
            cf = c.get("canonical_form", "")
            expr = ConstraintParser.parse(cf)
            if expr is None:
                continue
            for var in ConstraintParser.extract_variables(expr):
                b = ConstraintParser.extract_bounds(expr, var)
                if var not in all_bounds:
                    all_bounds[var] = {"min": None, "max": None}
                if b["min"] is not None:
                    if all_bounds[var]["min"] is None:
                        all_bounds[var]["min"] = b["min"]
                    else:
                        all_bounds[var]["min"] = max(all_bounds[var]["min"], b["min"])
                if b["max"] is not None:
                    if all_bounds[var]["max"] is None:
                        all_bounds[var]["max"] = b["max"]
                    else:
                        all_bounds[var]["max"] = min(all_bounds[var]["max"], b["max"])
        return all_bounds


# ── Consistency checker ─────────────────────────────────────
class ConsistencyChecker:
    def __init__(self):
        self._parser = ConstraintParser()

    def check_pair(self, constraint_a: dict, constraint_b: dict) -> str:
        cf_a = constraint_a.get("canonical_form", "")
        cf_b = constraint_b.get("canonical_form", "")
        expr_a = self._parser.parse(cf_a)
        expr_b = self._parser.parse(cf_b)
        if expr_a is None or expr_b is None:
            return "INDEPENDENT"

        vars_a = self._parser.extract_variables(expr_a)
        vars_b = self._parser.extract_variables(expr_b)
        if not vars_a & vars_b:
            return "INDEPENDENT"

        common_var = list(vars_a & vars_b)[0]
        bounds_a = self._parser.extract_bounds(expr_a, common_var)
        bounds_b = self._parser.extract_bounds(expr_b, common_var)

        min_a = bounds_a["min"] if bounds_a["min"] is not None else -math.inf
        max_a = bounds_a["max"] if bounds_a["max"] is not None else math.inf
        min_b = bounds_b["min"] if bounds_b["min"] is not None else -math.inf
        max_b = bounds_b["max"] if bounds_b["max"] is not None else math.inf

        if min_a > max_b or min_b > max_a:
            return "CONTRADICTORY"

        if self._is_redundant(min_a, max_a, min_b, max_b):
            return "REDUNDANT_A"
        if self._is_redundant(min_b, max_b, min_a, max_a):
            return "REDUNDANT_B"

        return "SATISFIABLE"

    @staticmethod
    def _is_redundant(min_a, max_a, min_b, max_b) -> bool:
        return min_a >= min_b and max_a <= max_b

    def full_check(self, constraints: List[dict]) -> ConsistencyReport:
        report = ConsistencyReport(constraints)
        n = len(constraints)
        for i in range(n):
            for j in range(i + 1, n):
                status = self.check_pair(constraints[i], constraints[j])
                name_a = constraints[i].get("identity_string", f"constraint_{i}")
                name_b = constraints[j].get("identity_string", f"constraint_{j}")
                cf_a = constraints[i].get("canonical_form", "")
                cf_b = constraints[j].get("canonical_form", "")
                if status == "CONTRADICTORY":
                    report.add_issue(
                        "CONTRADICTION", name_a, name_b,
                        f"'{cf_a}' and '{cf_b}' cannot both be true — no value satisfies both",
                        severity="CRITICAL",
                    )
                elif status in ("REDUNDANT_A", "REDUNDANT_B"):
                    if status == "REDUNDANT_A":
                        reason = f"'{cf_a}' is stricter than '{cf_b}', making B redundant"
                        report.add_issue("REDUNDANCY", name_a, name_b, reason, severity="WARNING")
                    else:
                        reason = f"'{cf_b}' is stricter than '{cf_a}', making A redundant"
                        report.add_issue("REDUNDANCY", name_b, name_a, reason, severity="WARNING")
        return report


# ── Satisfiability checker ──────────────────────────────────
class SatisfiabilityChecker:
    def __init__(self):
        self._parser = ConstraintParser()

    def is_satisfiable(self, constraints: List[dict]) -> bool:
        all_bounds = self._parser.extract_all_bounds(constraints)
        for var, bounds in all_bounds.items():
            lo = bounds.get("min")
            hi = bounds.get("max")
            if lo is not None and hi is not None and lo > hi:
                return False
        return True


# ── Coverage analyzer ───────────────────────────────────────
class CoverageAnalyzer:
    def __init__(self, common_variables: List[str] = None):
        self._common = common_variables or ["age", "income", "debt_ratio", "credit_score", "employment_status"]
        self._parser = ConstraintParser()

    def analyze(self, constraints: List[dict]) -> dict:
        covered: Set[str] = set()
        for c in constraints:
            expr = self._parser.parse(c.get("canonical_form", ""))
            if expr:
                covered.update(self._parser.extract_variables(expr))
        common_set = set(self._common)
        missing = common_set - covered
        return {
            "covered_variables": sorted(covered),
            "missing_variables": sorted(missing),
            "coverage_pct": round(len(covered & common_set) / len(common_set) * 100, 2) if common_set else 0,
        }


# ── Test case generator ─────────────────────────────────────
class TestCaseGenerator:
    def __init__(self):
        self._parser = ConstraintParser()

    def generate(self, constraints: List[dict]) -> List[dict]:
        bounds = self._parser.extract_all_bounds(constraints)
        tests = []
        for var, b in bounds.items():
            lo = b.get("min")
            hi = b.get("max")
            if lo is not None:
                tests.append({
                    "name": f"{var}_at_min",
                    "bindings": {var: lo},
                    "description": f"Test {var} at minimum bound ({lo})",
                })
                if isinstance(lo, int) and lo > -10**9:
                    tests.append({
                        "name": f"{var}_below_min",
                        "bindings": {var: lo - 1},
                        "description": f"Test {var} below minimum ({lo - 1})",
                    })
            if hi is not None:
                tests.append({
                    "name": f"{var}_at_max",
                    "bindings": {var: hi},
                    "description": f"Test {var} at maximum bound ({hi})",
                })
                if isinstance(hi, int) and hi < 10**9:
                    tests.append({
                        "name": f"{var}_above_max",
                        "bindings": {var: hi + 1},
                        "description": f"Test {var} above maximum ({hi + 1})",
                    })
            if lo is not None and hi is not None and lo < hi:
                mid = (lo + hi) // 2 if isinstance(lo, int) and isinstance(hi, int) else (lo + hi) / 2
                tests.append({
                    "name": f"{var}_mid_range",
                    "bindings": {var: mid},
                    "description": f"Test {var} at mid‑range ({mid})",
                })
        return tests
