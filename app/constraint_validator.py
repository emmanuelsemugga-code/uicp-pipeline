#!/usr/bin/env python3
"""
app/constraint_validator.py — GAP‑32 Constraint Validation Framework
Multi‑stage validation for constraints before deployment.
"""
import json, re
from abc import ABC, abstractmethod
from typing import List, Optional

class ValidationError:
    def __init__(self, error_type: str, message: str, constraint_index: int = 0,
                 field: str = "", suggestion: str = "", position: dict = None):
        self.error_type = error_type
        self.message = message
        self.constraint_index = constraint_index
        self.field = field
        self.suggestion = suggestion
        self.position = position or {}

    def __str__(self):
        parts = [f"{self.error_type} — {self.message}"]
        if self.constraint_index:
            parts.append(f"  Constraint #{self.constraint_index}")
        if self.field:
            parts.append(f"  Field: {self.field}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


class ValidationResult:
    def __init__(self, tenant_id: str = "", constraint_version: int = 0):
        self.tenant_id = tenant_id
        self.constraint_version = constraint_version
        self.syntax_errors: List[ValidationError] = []
        self.semantic_errors: List[ValidationError] = []
        self.logical_errors: List[ValidationError] = []
        self.performance_errors: List[ValidationError] = []
        self.compatibility_errors: List[ValidationError] = []
        self.warnings: List[str] = []

    @property
    def passed(self) -> bool:
        return not any([self.syntax_errors, self.semantic_errors,
                        self.logical_errors, self.performance_errors,
                        self.compatibility_errors])

    def all_errors(self) -> List[ValidationError]:
        return (self.syntax_errors + self.semantic_errors +
                self.logical_errors + self.performance_errors +
                self.compatibility_errors)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "tenant_id": self.tenant_id,
            "errors": [
                {"type": e.error_type, "message": e.message,
                 "constraint_index": e.constraint_index,
                 "field": e.field, "suggestion": e.suggestion}
                for e in self.all_errors()
            ],
            "warnings": self.warnings,
        }


class BaseValidator(ABC):
    @abstractmethod
    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        ...


def _get_constraints(constraint_set: dict) -> list:
    raw = constraint_set.get("canonical_constraints", constraint_set.get("constraints", []))
    if not isinstance(raw, list):
        return []
    return raw


REQUIRED_FIELDS = ["identity_string", "canonical_form", "classification"]
VALID_CLASSIFICATIONS = {"LINEAR_SINGLE_VAR", "LINEAR_MULTI_VAR",
                          "NONLINEAR", "LOGICAL", "CUSTOM"}
IDENTITY_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')

class SyntaxValidator(BaseValidator):
    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        constraints = _get_constraints(constraint_set)
        if not constraints and "canonical_constraints" in constraint_set:
            val = constraint_set["canonical_constraints"]
            if not isinstance(val, list):
                result.syntax_errors.append(ValidationError(
                    "SYNTAX_ERROR",
                    f"canonical_constraints must be an array, got {type(val).__name__}",
                    field="canonical_constraints",
                    suggestion="Wrap your constraints in an array: {\"canonical_constraints\": [...]}"
                ))
            return
        for i, c in enumerate(constraints):
            if not isinstance(c, dict):
                result.syntax_errors.append(ValidationError(
                    "SYNTAX_ERROR", f"Constraint #{i} must be a JSON object",
                    constraint_index=i, suggestion="Use {…} not a string or number"
                ))
                continue
            for field in REQUIRED_FIELDS:
                if field not in c:
                    result.syntax_errors.append(ValidationError(
                        "SYNTAX_ERROR", f"Missing required field '{field}'",
                        constraint_index=i, field=field,
                        suggestion=f"Add \"{field}\" to this constraint"
                    ))
            if "identity_string" in c and not IDENTITY_PATTERN.match(c["identity_string"]):
                result.syntax_errors.append(ValidationError(
                    "SYNTAX_ERROR",
                    f"identity_string '{c['identity_string']}' must be UPPER_SNAKE_CASE",
                    constraint_index=i, field="identity_string",
                    suggestion="Use only A‑Z, 0‑9, and underscores, e.g. AGE_MIN_18"
                ))
            if "classification" in c and c["classification"] not in VALID_CLASSIFICATIONS:
                result.syntax_errors.append(ValidationError(
                    "SYNTAX_ERROR",
                    f"Unknown classification '{c['classification']}'",
                    constraint_index=i, field="classification",
                    suggestion=f"Use one of: {', '.join(sorted(VALID_CLASSIFICATIONS))}"
                ))
            if "canonical_form" in c:
                cf = c["canonical_form"]
                if not isinstance(cf, str):
                    result.syntax_errors.append(ValidationError(
                        "SYNTAX_ERROR", "canonical_form must be a string",
                        constraint_index=i, field="canonical_form",
                        suggestion="Write the constraint as a string, e.g. \"age >= 18\""
                    ))
                elif len(cf) > 10_000:
                    result.syntax_errors.append(ValidationError(
                        "SYNTAX_ERROR", "canonical_form exceeds 10,000 character limit",
                        constraint_index=i, field="canonical_form",
                        suggestion="Break complex constraints into multiple smaller ones"
                    ))


_VALID_OPS = {">=", "<=", ">", "<", "==", "!=", "+", "-", "*", "(", ")"}

class SemanticValidator(BaseValidator):
    def __init__(self, binding_schema: dict = None):
        self._schema = binding_schema or {}

    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        constraints = _get_constraints(constraint_set)
        schema = binding_schema or self._schema
        for i, c in enumerate(constraints):
            if not isinstance(c, dict):
                continue
            cf = c.get("canonical_form", "")
            if not isinstance(cf, str) or not cf.strip():
                continue
            self._check_parentheses(cf, i, result)
            self._check_operators(cf, i, result)
            if schema:
                self._check_variables(cf, schema, i, result)

    def _check_parentheses(self, expr: str, idx: int, result: ValidationResult):
        depth = 0
        for pos, ch in enumerate(expr):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth < 0:
                result.semantic_errors.append(ValidationError(
                    "SEMANTIC_ERROR",
                    "Unmatched closing parenthesis",
                    constraint_index=idx,
                    position={"character": pos},
                    suggestion="Remove the extra ')' or add a matching '(' before it"
                ))
                return
        if depth > 0:
            result.semantic_errors.append(ValidationError(
                "SEMANTIC_ERROR",
                f"Unmatched opening parenthesis ({depth} missing ')')",
                constraint_index=idx,
                suggestion="Add closing parentheses or remove the unmatched '('"
            ))

    def _check_operators(self, expr: str, idx: int, result: ValidationResult):
        # Catch common invalid operator pairs before tokenisation
        invalid_patterns = [
            (r'=>', '=>', '>= (greater than or equal)'),
            (r'=<', '=<', '<='),
            (r'<\s*>', '< >', '!='),
        ]
        for pattern, display, suggestion in invalid_patterns:
            if re.search(pattern, expr):
                result.semantic_errors.append(ValidationError(
                    "SEMANTIC_ERROR",
                    f"Invalid operator: '{display}'",
                    constraint_index=idx,
                    suggestion=f"Did you mean '{suggestion}'?"
                ))
                return

        tokens = re.findall(r'[<>]=?|==|!=|[+\-*()]|[A-Za-z_]\w*|\d+', expr)
        for tok in tokens:
            if tok in _VALID_OPS:
                continue
            if re.match(r'^[A-Za-z_]\w*$', tok):
                continue
            if re.match(r'^\d+$', tok):
                continue
            result.semantic_errors.append(ValidationError(
                "SEMANTIC_ERROR",
                f"Unknown operator or token: '{tok}'",
                constraint_index=idx,
                suggestion=f"Valid operators are: {', '.join(sorted(_VALID_OPS - {'(',')'}))}"
            ))

    def _check_variables(self, expr: str, schema: dict, idx: int, result: ValidationResult):
        vars_in_expr = set(re.findall(r'[A-Za-z_]\w*', expr)) - {"AND", "OR", "NOT"}
        available = set(schema.keys()) if schema else set()
        for var in vars_in_expr:
            if var not in available:
                suggestion = ""
                if available:
                    suggestion = f"Available variables: {', '.join(sorted(available))}"
                result.semantic_errors.append(ValidationError(
                    "SEMANTIC_ERROR",
                    f"Variable '{var}' not found in binding schema",
                    constraint_index=idx,
                    suggestion=suggestion
                ))


class LogicalValidator(BaseValidator):
    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        constraints = _get_constraints(constraint_set)
        if len(constraints) < 2:
            return
        for i in range(len(constraints)):
            for j in range(i + 1, len(constraints)):
                a = constraints[i].get("canonical_form", "")
                b = constraints[j].get("canonical_form", "")
                if not isinstance(a, str) or not isinstance(b, str):
                    continue
                conflict = self._detect_contradiction(a, b)
                if conflict:
                    result.logical_errors.append(ValidationError(
                        "LOGICAL_ERROR",
                        f"Constraints #{i} and #{j} contradict each other",
                        suggestion=f"'{a}' and '{b}' cannot both be satisfied"
                    ))
                elif self._detect_redundancy(a, b):
                    result.warnings.append(
                        f"Constraint #{j} ('{b}') may be redundant — "
                        f"it is implied by constraint #{i} ('{a}')"
                    )

    @staticmethod
    def _parse_bound(expr: str) -> Optional[tuple]:
        m = re.match(r'^\s*(\w+)\s*(>=|<=|>|<|==)\s*(-?\d+)\s*$', expr)
        if not m:
            return None
        return m.group(1), m.group(2), int(m.group(3))

    @staticmethod
    def _detect_contradiction(a: str, b: str) -> bool:
        pa, pb = LogicalValidator._parse_bound(a), LogicalValidator._parse_bound(b)
        if not pa or not pb:
            return False
        va, oa, na = pa
        vb, ob, nb = pb
        if va != vb:
            return False
        if oa in (">=", ">") and ob in ("<=", "<"):
            if oa == ">=" and ob == "<=":
                return na > nb
            if oa == ">" and ob == "<":
                return na >= nb
            if oa == ">=" and ob == "<":
                return na >= nb
            if oa == ">" and ob == "<=":
                return na >= nb
        if ob in (">=", ">") and oa in ("<=", "<"):
            return LogicalValidator._detect_contradiction(b, a)
        return False

    @staticmethod
    def _detect_redundancy(a: str, b: str) -> bool:
        pa, pb = LogicalValidator._parse_bound(a), LogicalValidator._parse_bound(b)
        if not pa or not pb:
            return False
        va, oa, na = pa
        vb, ob, nb = pb
        if va != vb:
            return False
        if oa == ">" and ob == ">" and na > nb:
            return True
        if oa == ">=" and ob == ">=" and na > nb:
            return True
        if oa == ">" and ob == ">=" and na >= nb:
            return True
        if oa == "<" and ob == "<" and na < nb:
            return True
        if oa == "<=" and ob == "<=" and na < nb:
            return True
        return False


class PerformanceValidator(BaseValidator):
    MAX_OR_DEPTH = 10
    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        constraints = _get_constraints(constraint_set)
        for i, c in enumerate(constraints):
            if not isinstance(c, dict):
                continue
            cf = c.get("canonical_form", "")
            if not isinstance(cf, str):
                continue
            or_count = cf.upper().count(" OR ")
            if or_count > self.MAX_OR_DEPTH:
                result.performance_errors.append(ValidationError(
                    "PERFORMANCE_ERROR",
                    f"Expression contains {or_count} OR clauses (limit: {self.MAX_OR_DEPTH})",
                    constraint_index=i,
                    suggestion="Break into multiple smaller constraints"
                ))


class CompatibilityValidator(BaseValidator):
    def __init__(self, binding_schema: dict = None, system_version: int = 4):
        self._schema = binding_schema or {}
        self._version = system_version

    def validate(self, constraint_set: dict, result: ValidationResult,
                 binding_schema: dict = None) -> None:
        constraints = _get_constraints(constraint_set)
        schema = binding_schema or self._schema
        if not schema:
            return
        for i, c in enumerate(constraints):
            if not isinstance(c, dict):
                continue
            cf = c.get("canonical_form", "")
            if not isinstance(cf, str):
                continue
            vars_in_expr = set(re.findall(r'[A-Za-z_]\w*', cf)) - {"AND", "OR", "NOT"}
            missing = vars_in_expr - set(schema.keys())
            for var in missing:
                result.compatibility_errors.append(ValidationError(
                    "COMPATIBILITY_ERROR",
                    f"Variable '{var}' is not in the extraction schema",
                    constraint_index=i,
                    suggestion="Add this variable to the extraction schema or remove it from the constraint"
                ))


class ConstraintValidator:
    def __init__(self, binding_schema: dict = None, system_version: int = 4):
        self._stages: List[BaseValidator] = [
            SyntaxValidator(),
            SemanticValidator(binding_schema),
            LogicalValidator(),
            PerformanceValidator(),
            CompatibilityValidator(binding_schema, system_version),
        ]

    def validate(self, constraint_set: dict, tenant_id: str = "",
                 constraint_version: int = 0) -> ValidationResult:
        result = ValidationResult(tenant_id, constraint_version)
        for stage in self._stages:
            stage.validate(constraint_set, result)
        return result


if __name__ == "__main__":
    passed = failed = 0
    def check(label, condition):
        global passed, failed
        if condition: passed += 1; print(f"  PASS  {label}")
        else: failed += 1; print(f"  FAIL  {label}")

    print("=== GAP‑32 Constraint Validator Test Suite ===\n")
    v = ConstraintValidator(binding_schema={"age": "int", "income": "float"})

    print("--- Stage 1: Syntax ---")
    r = v.validate({"canonical_constraints": "not_a_list"})
    check("Rejects non‑array", not r.passed and any("array" in e.message for e in r.syntax_errors))

    r = v.validate({"canonical_constraints": [
        {"identity_string": "BAD NAME", "canonical_form": "x>1", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Rejects bad identity_string", not r.passed and any("UPPER" in e.message for e in r.syntax_errors))

    r = v.validate({"canonical_constraints": [
        {"identity_string": "C1", "canonical_form": "x>1", "classification": "UNKNOWN"}
    ]})
    check("Rejects bad classification", not r.passed)

    r = v.validate({"canonical_constraints": [
        {"identity_string": "C1", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Missing canonical_form detected", not r.passed and any("canonical_form" in e.message for e in r.syntax_errors))

    print("\n--- Stage 2: Semantic ---")
    r = v.validate({"canonical_constraints": [
        {"identity_string": "OK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Valid constraint passes semantic", not r.semantic_errors)

    r = v.validate({"canonical_constraints": [
        {"identity_string": "BAD", "canonical_form": "unknown_var >= 5", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Unknown variable detected", not r.passed and any("unknown_var" in e.message for e in r.semantic_errors))

    r = v.validate({"canonical_constraints": [
        {"identity_string": "BAD", "canonical_form": "age => 18", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Bad operator detected", not r.passed and any("=>" in e.message for e in r.semantic_errors))

    print("\n--- Stage 3: Logical ---")
    r = v.validate({"canonical_constraints": [
        {"identity_string": "A", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"},
        {"identity_string": "B", "canonical_form": "age < 18", "classification": "LINEAR_SINGLE_VAR"},
    ]})
    check("Contradiction detected", not r.passed and any("contradict" in e.message for e in r.logical_errors))

    r = v.validate({"canonical_constraints": [
        {"identity_string": "A", "canonical_form": "age > 21", "classification": "LINEAR_SINGLE_VAR"},
        {"identity_string": "B", "canonical_form": "age > 18", "classification": "LINEAR_SINGLE_VAR"},
    ]})
    check("Redundancy warning", any("redundant" in w.lower() for w in r.warnings))

    print("\n--- Stage 4: Performance ---")
    many_or = " OR ".join([f"x == {i}" for i in range(15)])
    r = v.validate({"canonical_constraints": [
        {"identity_string": "BIG", "canonical_form": many_or, "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Excessive OR clauses detected", not r.passed and any("OR" in e.message for e in r.performance_errors))

    print("\n--- Stage 5: Compatibility ---")
    r = v.validate({"canonical_constraints": [
        {"identity_string": "BAD", "canonical_form": "credit >= 700", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Missing schema variable detected", not r.passed and any("credit" in e.message for e in r.compatibility_errors))

    r = v.validate({"canonical_constraints": [
        {"identity_string": "OK", "canonical_form": "age >= 18", "classification": "LINEAR_SINGLE_VAR"}
    ]})
    check("Valid schema passes all stages", r.passed)

    total = passed + failed
    print(f"\n=== Results: {passed}/{total} passed ===")
    if failed == 0:
        print("✓ GAP‑32 Constraint Validator VALIDATED — ready for commit\n")
    else:
        print("✗ FIX FAILURES BEFORE COMMIT\n")
