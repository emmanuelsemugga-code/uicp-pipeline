#!/usr/bin/env python3
"""
binding_extraction.py — Deterministic Binding‑Extraction Layer (v1.1)
Converts raw model text output into numeric bindings for the Phase 4
enforcement gateway.  No floats, no randomness, no model calls.
"""
import json
import re

INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1


def extract_bindings(model_output: str, binding_schema: dict) -> dict:
    bindings = {}
    missing = []

    for var_name, rule in binding_schema.items():
        method = rule.get("method")
        value = None

        if method == "constant":
            value = _extract_constant(rule)
        elif method == "regex":
            value = _extract_regex(model_output, rule, var_name)
        elif method == "jsonpath":
            value = _extract_jsonpath(model_output, rule, var_name)
        elif method == "tag":
            value = _extract_tag(model_output, rule, var_name)
        else:
            missing.append(var_name)
            continue

        if value is None:
            missing.append(var_name)
        else:
            bindings[var_name] = value

    if missing:
        return {
            "status": "INCOMPLETE",
            "bindings": bindings,
            "missing": missing,
        }
    return {
        "status": "COMPLETE",
        "bindings": bindings,
    }


def _extract_constant(rule: dict):
    val = rule.get("value")
    if isinstance(val, bool):
        return None
    if not isinstance(val, int):
        return None
    if not (INT128_MIN <= val <= INT128_MAX):
        return None
    return val


def _extract_regex(model_output: str, rule: dict, var_name: str):
    pattern = rule.get("pattern")
    if not pattern or not isinstance(pattern, str):
        return None
    try:
        compiled = re.compile(pattern)
    except re.error:
        return None
    match = compiled.search(model_output)
    if not match:
        return None
    try:
        captured = match.group("value")
    except IndexError:
        return None
    if captured is None:
        return None
    return _parse_int(captured)


def _extract_jsonpath(model_output: str, rule: dict, var_name: str):
    path = rule.get("path")
    if not path or not isinstance(path, str):
        return None

    obj = None
    try:
        obj = json.loads(model_output)
    except (json.JSONDecodeError, TypeError):
        start = model_output.find("{")
        end = model_output.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(model_output[start:end+1])
            except (json.JSONDecodeError, TypeError):
                pass

    if obj is None:
        return None

    keys = path.split(".")
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return _parse_int(current)


def _extract_tag(model_output: str, rule: dict, var_name: str):
    tag_name = rule.get("tag")
    if not tag_name or not isinstance(tag_name, str):
        return None
    opening = f"[VAR:{tag_name}]"
    closing = f"[/VAR]"
    start_idx = model_output.find(opening)
    if start_idx == -1:
        return None
    start_idx += len(opening)
    end_idx = model_output.find(closing, start_idx)
    if end_idx == -1:
        return None
    captured = model_output[start_idx:end_idx].strip()
    return _parse_int(captured)


def _parse_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if INT128_MIN <= value <= INT128_MAX:
            return value
        return None
    if isinstance(value, str):
        stripped = value.strip()
        try:
            val = int(stripped)
        except ValueError:
            return None
        if INT128_MIN <= val <= INT128_MAX:
            return val
    return None
  # ---------------------------------------------------------------------------
# Built‑in test harness (17 checks)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    PASS = FAIL = 0

    def check(label, condition, detail=""):
        global PASS, FAIL
        if condition:
            PASS += 1
            print(f"  ✓  {label}")
        else:
            FAIL += 1
            print(f"  ✗  {label}  —  {detail}")

    print("=== Binding‑Extraction Layer Test Suite (v1.1) ===\n")

    # 1. Valid regex extraction (case‑insensitive)
    print("1. Valid regex extraction")
    schema = {"risk": {"method": "regex", "pattern": r"(?i)single[ -]position risk[ =:]+(?P<value>-?\d+)"}}
    output = "Portfolio analysis complete. Single-position risk = 27. Recommended."
    result = extract_bindings(output, schema)
    check("status COMPLETE", result["status"] == "COMPLETE")
    check("risk = 27", result["bindings"].get("risk") == 27)

    # 2. Non‑matching regex
    print("\n2. Non‑matching regex")
    output2 = "No risk data available."
    result2 = extract_bindings(output2, schema)
    check("status INCOMPLETE", result2["status"] == "INCOMPLETE")
    check("risk in missing", "risk" in result2.get("missing", []))

    # 3. Valid JSONPath extraction
    print("\n3. Valid JSONPath extraction")
    schema3 = {"age": {"method": "jsonpath", "path": "client.age"}}
    output3 = '{"client": {"name": "Alice", "age": 42}}'
    result3 = extract_bindings(output3, schema3)
    check("status COMPLETE", result3["status"] == "COMPLETE")
    check("age = 42", result3["bindings"].get("age") == 42)

    # 4. Invalid JSONPath
    print("\n4. Invalid JSONPath (wrong path)")
    output4 = '{"client": {"name": "Bob"}}'
    result4 = extract_bindings(output4, schema3)
    check("status INCOMPLETE", result4["status"] == "INCOMPLETE")

    # 5. Valid tag extraction
    print("\n5. Valid tag extraction")
    schema5 = {"loan": {"method": "tag", "tag": "LOAN_AMOUNT"}}
    output5 = "Recommendation: approve loan of [VAR:LOAN_AMOUNT]15000[/VAR] to customer."
    result5 = extract_bindings(output5, schema5)
    check("status COMPLETE", result5["status"] == "COMPLETE")
    check("loan = 15000", result5["bindings"].get("loan") == 15000)

    # 6. Constant extraction
    print("\n6. Constant extraction (independent of model output)")
    schema6 = {"max_exposure": {"method": "constant", "value": 1_000_000}}
    result6 = extract_bindings("any output", schema6)
    check("status COMPLETE", result6["status"] == "COMPLETE")
    check("max_exposure = 1,000,000", result6["bindings"].get("max_exposure") == 1_000_000)

    # 7. Mixed schema (regex + constant + JSONPath) — JSON object embedded in text
    print("\n7. Mixed schema (regex + constant + JSONPath)")
    schema7 = {
        "risk": {"method": "regex", "pattern": r"risk[ =:]+(?P<value>-?\d+)"},
        "max_exposure": {"method": "constant", "value": 500_000},
        "age": {"method": "jsonpath", "path": "client.age"},
    }
    output7 = '{"client": {"age": 35}}  risk = 12  '
    result7 = extract_bindings(output7, schema7)
    check("status COMPLETE", result7["status"] == "COMPLETE")
    check("risk = 12", result7["bindings"].get("risk") == 12)
    check("max_exposure = 500,000", result7["bindings"].get("max_exposure") == 500_000)
    check("age = 35", result7["bindings"].get("age") == 35)

    # 8. Empty model output
    print("\n8. Empty model output")
    schema8 = {"risk": {"method": "regex", "pattern": r"risk[ =:]+(?P<value>-?\d+)"}}
    result8 = extract_bindings("", schema8)
    check("status INCOMPLETE", result8["status"] == "INCOMPLETE")
    check("risk in missing", "risk" in result8.get("missing", []))

    total = PASS + FAIL
    print(f"\n=== Results: {PASS}/{total} passed ===")
