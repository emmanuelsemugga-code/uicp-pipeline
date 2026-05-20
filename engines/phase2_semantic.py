#!/usr/bin/env python3
"""
phase2_public.py – Public Phase 2 interface.
Imports the internal engine and only exposes the validated output contract.
No internal algorithms are revealed.

VALIDATED: Colab 2025‑05‑07 — Status OK, Determinism True.
"""
import sys
import json
import hashlib

import phase2_engine as _engine


def phase2_verify(
    constraints: list,
    identities: list,
    stats: dict,
    admission_status: str = "ACCEPT",
    execution_bindings: dict = None,
) -> dict:
    if admission_status != "ACCEPT":
        return {
            "status": "REJECTED",
            "reason": "admission_status must be 'ACCEPT'",
            "reduced_constraints": [],
            "equivalence_groups": [],
            "dominance_removed": [],
            "execution_result": None,
        }
    if len(constraints) != len(identities):
        return {
            "status": "REJECTED",
            "reason": "constraints and identities must have the same length",
            "reduced_constraints": [],
            "equivalence_groups": [],
            "dominance_removed": [],
            "execution_result": None,
        }
    result = _engine.phase2_engine(
        constraints,
        identities,
        stats,
        admission_status,
        execution_bindings=execution_bindings,
    )
    return result
