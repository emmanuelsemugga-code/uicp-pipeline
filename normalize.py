#!/usr/bin/env python3
"""
normalize.py – Public interface for Phase 1 normalization.
Imports the internal engine but only exposes the normalised identity strings.
No pipeline details, admission‑gate logic, or AST are visible.
"""
import sys
import json

# internal engine – DO NOT PUBLISH
import normalize_v05 as _engine

def normalize(constraint_str: str, available_vars: set = None) -> str:
    """
    Return the canonical identity string for a single constraint.
    On failure the function prints REJECT+HALT and exits.
    """
    if available_vars is None:
        available_vars = set()
    input_data = {
        "objective_commitment": "PUBLIC_API",
        "constraint_set": [constraint_str],
        "input_set": {v: 0 for v in available_vars},
    }
    result = _engine.NORMALIZE(input_data)
    if result["result"] != "OK":
        print(f"REJECT+HALT: {result.get('reason','unknown')}")
        sys.exit(1)
    # The output is a list of identity strings; for a single constraint we return the first.
    return result["constraints"][0]

def normalize_set(constraints: list, available_vars: set = None) -> list:
    """Return the sorted list of canonical identity strings for a set of constraints."""
    if available_vars is None:
        available_vars = set()
    input_data = {
        "objective_commitment": "PUBLIC_API",
        "constraint_set": constraints,
        "input_set": {v: 0 for v in available_vars},
    }
    result = _engine.NORMALIZE(input_data)
    if result["result"] != "OK":
        print(f"REJECT+HALT: {result.get('reason','unknown')}")
        sys.exit(1)
    return result["constraints"]
