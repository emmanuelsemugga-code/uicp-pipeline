#!/usr/bin/env python3
"""
app/constraint_priority.py — GAP‑35 Constraint Conflict Resolution & Priority Ordering
Resolves conflicts between constraints using priority levels and deterministic
ordering, ensuring consistent enforcement when constraints overlap.
"""
import json, uuid
from typing import List, Dict, Optional, Tuple
from enum import IntEnum
from collections import defaultdict


# ── Priority levels ─────────────────────────────────────────
class PriorityLevel(IntEnum):
    CRITICAL = 1   # Highest priority — must be enforced first
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    DEFAULT = 5   # Lowest priority — applied last


# ── Data structures ─────────────────────────────────────────
class PriorityConstraint:
    def __init__(self, identity_string: str, canonical_form: str,
                 priority: PriorityLevel = PriorityLevel.DEFAULT,
                 overridable: bool = True):
        self.identity_string = identity_string
        self.canonical_form = canonical_form
        self.priority = priority
        self.overridable = overridable
        self.order: int = 0

    def to_dict(self) -> dict:
        return {
            "identity_string": self.identity_string,
            "canonical_form": self.canonical_form,
            "priority": int(self.priority),
            "priority_name": self.priority.name,
            "overridable": self.overridable,
            "order": self.order,
        }


class ConflictRecord:
    def __init__(self, constraint_a: str, constraint_b: str,
                 resolution: str, reason: str = ""):
        self.constraint_a = constraint_a
        self.constraint_b = constraint_b
        self.resolution = resolution
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "constraint_a": self.constraint_a,
            "constraint_b": self.constraint_b,
            "resolution": self.resolution,
            "reason": self.reason,
        }


# ── Priority manager ────────────────────────────────────────
class ConstraintPriorityManager:
    def __init__(self):
        self._priorities: Dict[str, Dict[str, PriorityConstraint]] = defaultdict(dict)
        self._conflicts: Dict[str, List[ConflictRecord]] = defaultdict(list)

    def register(self, tenant_id: str, constraint_name: str,
                 canonical_form: str,
                 priority: PriorityLevel = PriorityLevel.DEFAULT,
                 overridable: bool = True):
        self._priorities[tenant_id][constraint_name] = PriorityConstraint(
            identity_string=constraint_name,
            canonical_form=canonical_form,
            priority=priority,
            overridable=overridable,
        )

    def get_priority(self, tenant_id: str,
                     constraint_name: str) -> PriorityLevel:
        entry = self._priorities.get(tenant_id, {}).get(constraint_name)
        return entry.priority if entry else PriorityLevel.DEFAULT

    def is_overridable(self, tenant_id: str, constraint_name: str) -> bool:
        entry = self._priorities.get(tenant_id, {}).get(constraint_name)
        return entry.overridable if entry else True

    def resolve_conflict(self, tenant_id: str,
                         constraint_a: str, constraint_b: str) -> Tuple[str, str]:
        pri_a = self.get_priority(tenant_id, constraint_a)
        pri_b = self.get_priority(tenant_id, constraint_b)

        if pri_a < pri_b:
            winner, loser = constraint_a, constraint_b
            reason = f"Higher priority ({pri_a.name} > {pri_b.name})"
        elif pri_b < pri_a:
            winner, loser = constraint_b, constraint_a
            reason = f"Higher priority ({pri_b.name} > {pri_a.name})"
        else:
            over_a = self.is_overridable(tenant_id, constraint_a)
            over_b = self.is_overridable(tenant_id, constraint_b)
            if over_a and not over_b:
                winner, loser = constraint_b, constraint_a
                reason = f"{constraint_b} is non‑overridable"
            elif over_b and not over_a:
                winner, loser = constraint_a, constraint_b
                reason = f"{constraint_a} is non‑overridable"
            else:
                winner, loser = sorted([constraint_a, constraint_b])[0], sorted([constraint_a, constraint_b])[1]
                reason = "Same priority — deterministic alphabetical order"

        rec = ConflictRecord(constraint_a, constraint_b, winner, reason)
        self._conflicts[tenant_id].append(rec)
        return winner, reason

    def order_by_priority(self, tenant_id: str,
                          constraint_names: List[str]) -> List[str]:
        pairs = []
        for name in constraint_names:
            pri = self.get_priority(tenant_id, name)
            pairs.append((int(pri), name))
        pairs.sort()
        return [name for _, name in pairs]

    def get_conflict_history(self, tenant_id: str) -> List[ConflictRecord]:
        return self._conflicts.get(tenant_id, [])

    def clear_conflicts(self, tenant_id: str):
        self._conflicts[tenant_id] = []
