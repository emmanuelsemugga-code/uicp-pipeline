#!/usr/bin/env python3
"""
Consumer-Facing Explanation Generator
Converts UICP enforcement decisions into plain-language explanations
for affected individuals.

Takes enforcement JSON and produces human-readable text explaining
approval or specific denial reasons.
"""
import re
from typing import Dict, List, Optional, Tuple, Any


class ConstraintComponentParser:
    @staticmethod
    def parse(canonical_form: str) -> Optional[Tuple[str, str, str]]:
        # FIXED: pattern now captures both numeric and string values
        pattern = r'^\s*(\w+)\s*(>=|<=|>|<|==|!=)\s*(-?\d+(?:\.\d+)?|\w+)\s*$'
        match = re.match(pattern, canonical_form.strip())
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None

    @staticmethod
    def parse_compound(canonical_form: str) -> List[Tuple[str, str, str]]:
        clauses = re.split(r'\s+(AND|OR)\s+', canonical_form)
        results = []
        for clause in clauses:
            if clause.upper() in ('AND', 'OR'):
                continue
            parsed = ConstraintComponentParser.parse(clause.strip())
            if parsed:
                results.append(parsed)
        return results


class VariableHumanizer:
    FRIENDLY_NAMES = {
        "age": "your age",
        "credit_score": "your credit score",
        "income": "your annual income",
        "debt_ratio": "your debt-to-income ratio",
        "employment_status": "your employment status",
        "is_student": "student status",
        "years_employed": "years of employment",
        "savings_balance": "your savings balance",
        "loan_amount": "the loan amount",
        "interest_rate": "the interest rate",
    }

    @staticmethod
    def humanize(variable_name: str) -> str:
        return VariableHumanizer.FRIENDLY_NAMES.get(
            variable_name.lower(),
            variable_name.replace("_", " ").lower()
        )


class OperatorHumanizer:
    OPERATOR_PHRASES = {
        ">=": "at least",
        "<=": "at most",
        ">": "greater than",
        "<": "less than",
        "==": "equal to",
        "!=": "not equal to",
    }

    @staticmethod
    def humanize(operator: str, is_failure: bool = True) -> str:
        return OperatorHumanizer.OPERATOR_PHRASES.get(operator, operator)


class UnitFormatter:
    @staticmethod
    def format_value(variable_name: str, value: Any) -> str:
        var_lower = variable_name.lower()
        try:
            num_val = float(value)
        except (ValueError, TypeError):
            return str(value)

        if var_lower in ("income", "loan_amount", "savings_balance"):
            return f"${num_val:,.0f}"
        if var_lower in ("age", "years_employed"):
            return f"{int(num_val)} years"
        if var_lower in ("debt_ratio", "interest_rate"):
            return f"{num_val:.1f}%"
        if num_val == int(num_val):
            return f"{int(num_val):,}"
        return f"{num_val:,.2f}"


class ConstraintExplainer:
    @staticmethod
    def explain_violation(constraint_name: str, canonical_form: str,
                         actual_value: Any, binding_value: Any = None) -> Optional[str]:
        parsed = ConstraintComponentParser.parse(canonical_form)
        if not parsed:
            return f"Constraint '{constraint_name}' was not satisfied"

        var_name, operator, threshold_str = parsed
        actual = binding_value if binding_value is not None else actual_value

        var_human = VariableHumanizer.humanize(var_name)
        actual_fmt = UnitFormatter.format_value(var_name, actual)
        threshold_fmt = UnitFormatter.format_value(var_name, threshold_str)
        op_phrase = OperatorHumanizer.humanize(operator, is_failure=True)

        return f"{var_human.capitalize()} ({actual_fmt}) must be {op_phrase} {threshold_fmt}"

    @staticmethod
    def explain_satisfaction(constraint_name: str, canonical_form: str,
                             actual_value: Any, binding_value: Any = None) -> Optional[str]:
        parsed = ConstraintComponentParser.parse(canonical_form)
        if not parsed:
            return f"Constraint '{constraint_name}' was satisfied"

        var_name, operator, threshold_str = parsed
        actual = binding_value if binding_value is not None else actual_value

        var_human = VariableHumanizer.humanize(var_name)
        actual_fmt = UnitFormatter.format_value(var_name, actual)
        threshold_fmt = UnitFormatter.format_value(var_name, threshold_str)

        if operator in (">=", ">"):
            phrase = f"meets the minimum ({threshold_fmt})"
        elif operator in ("<=", "<"):
            phrase = f"meets the maximum ({threshold_fmt})"
        elif operator == "==":
            phrase = f"equals ({threshold_fmt})"
        else:
            phrase = f"satisfies the requirement ({threshold_fmt})"

        return f"{var_human.capitalize()} ({actual_fmt}) {phrase}"


class DecisionExplainer:
    def __init__(self, use_detailed_format: bool = False):
        self.use_detailed_format = use_detailed_format

    def explain(self, enforcement_decision: Dict[str, Any]) -> str:
        decision = enforcement_decision.get("decision", "UNKNOWN")
        bindings = enforcement_decision.get("bindings", {})
        failed = enforcement_decision.get("failed_constraints", [])
        satisfied = enforcement_decision.get("satisfied_constraints", [])

        if decision == "ALLOW":
            outcome = "Your request was approved."
        elif decision == "BLOCK":
            outcome = "Your request was declined."
        else:
            return f"Decision: {decision}"

        if any(c.get("constraint_name") == "MISSING_VARIABLE" for c in failed):
            outcome += " We were unable to process your request due to missing information."
            return outcome

        explanation_lines = [outcome]

        if decision == "BLOCK" and failed:
            explanation_lines.append("The following requirements were not met:")
            for constraint in failed:
                name = constraint.get("constraint_name", "Unknown")
                canonical_form = constraint.get("canonical_form", "")
                actual = bindings.get(self._extract_variable(canonical_form))
                explanation = ConstraintExplainer.explain_violation(name, canonical_form, actual)
                if explanation:
                    explanation_lines.append(f"• {explanation}")

        elif decision == "ALLOW" and self.use_detailed_format and satisfied:
            explanation_lines.append("The following requirements were met:")
            for constraint in satisfied:
                name = constraint.get("constraint_name", "Unknown")
                canonical_form = constraint.get("canonical_form", "")
                actual = bindings.get(self._extract_variable(canonical_form))
                explanation = ConstraintExplainer.explain_satisfaction(name, canonical_form, actual)
                if explanation:
                    explanation_lines.append(f"• {explanation}")

        if decision == "BLOCK":
            explanation_lines.append("\nIf you believe this is an error, please contact support.")

        return "\n".join(explanation_lines)

    @staticmethod
    def _extract_variable(canonical_form: str) -> str:
        match = re.match(r'^\s*(\w+)\s*', canonical_form)
        return match.group(1) if match else ""
