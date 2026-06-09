#!/usr/bin/env python3
"""
app/constraint_inheritance.py — GAP‑23 Constraint Set Inheritance & Templating
Enables constraint reuse through parent‑child inheritance trees, override detection,
automatic propagation, and conflict resolution.
"""
import json, uuid, time, re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict


# ── Data structures ─────────────────────────────────────────
class ConstraintSource(Enum):
    INHERITED = "inherited"
    OVERRIDDEN = "overridden"
    OWN = "own"
    UNKNOWN = "unknown"


class OverrideInfo:
    def __init__(self, constraint_name: str, parent_value: str,
                 child_value: str, is_override: bool = True):
        self.constraint_name = constraint_name
        self.parent_value = parent_value
        self.child_value = child_value
        self.is_override = is_override

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "parent_value": self.parent_value,
            "child_value": self.child_value,
            "is_override": self.is_override,
        }


class ConflictInfo:
    def __init__(self, conflict_type: str, severity: str, message: str):
        self.type = conflict_type
        self.severity = severity
        self.message = message

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
        }


class ConstraintInheritanceRelationship:
    def __init__(self, relationship_id: str = "", child_version: int = 0,
                 parent_versions: List[int] = None,
                 overrides: Dict[str, dict] = None,
                 created_by: str = "", status: str = "ACTIVE",
                 superseded_by: int = None):
        self.relationship_id = relationship_id or str(uuid.uuid4())[:8]
        self.child_version = child_version
        self.parent_versions = parent_versions or []
        self.overrides = overrides or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.created_by = created_by
        self.status = status
        self.superseded_by = superseded_by

    def to_dict(self) -> dict:
        return {
            "relationship_id": self.relationship_id,
            "child_version": self.child_version,
            "parent_versions": self.parent_versions,
            "overrides": self.overrides,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "status": self.status,
            "superseded_by": self.superseded_by,
        }


class ConstraintInheritanceTree:
    def __init__(self):
        self.children: Dict[int, List[int]] = defaultdict(list)
        self.parents: Dict[int, List[int]] = {}
        self.relationships: Dict[str, ConstraintInheritanceRelationship] = {}

    def add_relationship(self, rel: ConstraintInheritanceRelationship):
        self.relationships[rel.relationship_id] = rel
        for pv in rel.parent_versions:
            if rel.child_version not in self.children[pv]:
                self.children[pv].append(rel.child_version)
        self.parents[rel.child_version] = rel.parent_versions

    def get_children_of(self, version: int) -> List[int]:
        return self.children.get(version, [])

    def get_parents_of(self, version: int) -> List[int]:
        return self.parents.get(version, [])

    def supersede_relationship(self, rel_id: str, new_version: int):
        rel = self.relationships.get(rel_id)
        if rel:
            rel.status = "SUPERSEDED"
            rel.superseded_by = new_version


class OverrideDetector:
    @staticmethod
    def detect_override(parent_constraint: dict, child_constraint: dict) -> Optional[OverrideInfo]:
        if parent_constraint.get("identity_string") != child_constraint.get("identity_string"):
            return None
        parent_cf = parent_constraint.get("canonical_form", "")
        child_cf = child_constraint.get("canonical_form", "")
        if parent_cf == child_cf:
            return None
        return OverrideInfo(
            constraint_name=parent_constraint.get("identity_string", ""),
            parent_value=parent_cf,
            child_value=child_cf,
            is_override=True,
        )

    @staticmethod
    def detect_conflict(parent_constraint: dict, child_override: dict) -> Optional[ConflictInfo]:
        parent_cf = parent_constraint.get("canonical_form", "")
        child_cf = child_override.get("canonical_form", "")
        parent_bounds = OverrideDetector._parse_bounds(parent_cf)
        child_bounds = OverrideDetector._parse_bounds(child_cf)
        if parent_bounds is None or child_bounds is None:
            return None
        p_var, p_op, p_val = parent_bounds
        c_var, c_op, c_val = child_bounds
        if p_var != c_var:
            return None
        if p_op in (">=", ">") and c_op in ("<=", "<"):
            p_effective = p_val if p_op == ">=" else p_val
            c_effective = c_val if c_op == "<=" else c_val
            if p_effective > c_effective:
                return ConflictInfo("CONTRADICTORY", "CRITICAL",
                                    f"Parent min {p_effective} > child max {c_effective}")
        if c_op in (">=", ">") and p_op in ("<=", "<"):
            c_effective = c_val if c_op == ">=" else c_val
            p_effective = p_val if p_op == "<=" else p_val
            if c_effective > p_effective:
                return ConflictInfo("CONTRADICTORY", "CRITICAL",
                                    f"Child min {c_effective} > parent max {p_effective}")
        if p_op in (">=", ">") and c_op in (">=", ">"):
            p_effective = p_val if p_op == ">=" else p_val
            c_effective = c_val if c_op == ">=" else c_val
            if c_effective < p_effective:
                return ConflictInfo("REDUNDANT_OVERRIDE", "WARNING",
                                    f"Child override is less restrictive than parent")
        if p_op in ("<=", "<") and c_op in ("<=", "<"):
            p_effective = p_val if p_op == "<=" else p_val
            c_effective = c_val if c_op == "<=" else c_val
            if c_effective > p_effective:
                return ConflictInfo("REDUNDANT_OVERRIDE", "WARNING",
                                    f"Child override is less restrictive than parent")
        return None

    @staticmethod
    def _parse_bounds(canonical_form: str) -> Optional[Tuple[str, str, float]]:
        m = re.match(r'^\s*(\w+)\s*(>=|<=|>|<|==)\s*(-?\d+(?:\.\d+)?)\s*$', canonical_form)
        if not m:
            return None
        var, op, val_str = m.group(1), m.group(2), m.group(3)
        try:
            return var, op, float(val_str)
        except ValueError:
            return None


# ── Stub constraint store for Colab ─────────────────────────
class _StubConstraintStore:
    def __init__(self):
        self._versions: Dict[int, dict] = {}
        self._next_version = 1
        self._active = 1

    def create_version(self, tenant_id: str, name: str,
                       constraints: List[dict], metadata: dict = None) -> int:
        v = self._next_version
        self._next_version += 1
        self._versions[v] = {
            "version": v,
            "name": name,
            "tenant_id": tenant_id,
            "canonical_constraints": list(constraints),
            "metadata": metadata or {},
        }
        return v

    def get_constraints(self, tenant_id: str, version: int) -> Optional[dict]:
        c = self._versions.get(version)
        if c and c.get("tenant_id") == tenant_id:
            return dict(c)
        return None

    def get_current_version(self, tenant_id: str) -> int:
        return self._active

    def get_metadata(self, tenant_id: str, version: int) -> dict:
        c = self._versions.get(version, {})
        return c.get("metadata", {})


# ── Constraint Inheritance Manager ──────────────────────────
class ConstraintInheritanceManager:
    def __init__(self, constraint_store: _StubConstraintStore = None):
        self.store = constraint_store or _StubConstraintStore()
        self.trees: Dict[str, ConstraintInheritanceTree] = {}
        self.override_detector = OverrideDetector()

    def create_child_set(
        self, tenant_id: str, child_name: str,
        parent_versions: List[int],
        overrides: Dict[str, dict] = None,
        new_constraints: List[dict] = None,
        created_by: str = "",
    ) -> int:
        overrides = overrides or {}
        new_constraints = new_constraints or []

        parent_sets = []
        for pv in parent_versions:
            ps = self.store.get_constraints(tenant_id, pv)
            if not ps:
                raise ValueError(f"Parent version {pv} not found for tenant {tenant_id}")
            parent_sets.append(ps)

        merged = self._merge_parents(parent_sets)
        inherited = {}
        overridden = {}

        for c in merged:
            cname = c.get("identity_string", "")
            if cname in overrides:
                override_entry = overrides[cname]
                conflict = self.override_detector.detect_conflict(c, override_entry)
                if conflict and conflict.severity == "CRITICAL":
                    raise ValueError(conflict.message)
                overridden[cname] = {
                    "identity_string": cname,
                    "canonical_form": override_entry.get("canonical_form", c.get("canonical_form", "")),
                    "classification": c.get("classification", "LINEAR_SINGLE_VAR"),
                }
            else:
                inherited[cname] = dict(c)

        own = {}
        for c in new_constraints:
            cname = c.get("identity_string", "")
            own[cname] = dict(c)

        all_constraints = {**inherited, **overridden, **own}

        metadata = {
            "type": "inherited",
            "parent_versions": parent_versions,
            "overrides": {k: v for k, v in overridden.items()},
            "own_constraints": {k: v for k, v in own.items()},
            "inherited_constraints": {k: v for k, v in inherited.items()},
            "composed_from": parent_versions if len(parent_versions) > 1 else None,
        }

        child_version = self.store.create_version(
            tenant_id=tenant_id,
            name=child_name,
            constraints=list(all_constraints.values()),
            metadata=metadata,
        )

        # Track relationship
        if tenant_id not in self.trees:
            self.trees[tenant_id] = ConstraintInheritanceTree()
        rel = ConstraintInheritanceRelationship(
            child_version=child_version,
            parent_versions=parent_versions,
            overrides={k: v for k, v in overridden.items()},
            created_by=created_by,
        )
        self.trees[tenant_id].add_relationship(rel)

        return child_version

    def update_parent_constraint(
        self, tenant_id: str, parent_version: int,
        constraint_name: str, new_canonical_form: str,
        updated_by: str = "",
    ) -> Dict[str, int]:
        parent = self.store.get_constraints(tenant_id, parent_version)
        if not parent:
            raise ValueError(f"Parent version {parent_version} not found")

        new_constraints = []
        for c in parent["canonical_constraints"]:
            nc = dict(c)
            if nc.get("identity_string") == constraint_name:
                nc["canonical_form"] = new_canonical_form
            new_constraints.append(nc)

        new_parent_version = self.store.create_version(
            tenant_id=tenant_id,
            name=parent["name"],
            constraints=new_constraints,
            metadata={"type": "parent_update", "updated_from": parent_version},
        )

        updated_children: Dict[str, int] = {}
        tree = self.trees.get(tenant_id)
        if not tree:
            return updated_children

        child_versions = tree.get_children_of(parent_version)
        for cv in child_versions:
            child = self.store.get_constraints(tenant_id, cv)
            if not child:
                continue
            meta = child.get("metadata", {})
            child_overrides = meta.get("overrides", {})

            if constraint_name in child_overrides:
                continue  # child overrides this — skip

            new_child_constraints = []
            for c in child["canonical_constraints"]:
                nc = dict(c)
                if nc.get("identity_string") == constraint_name:
                    nc["canonical_form"] = new_canonical_form
                new_child_constraints.append(nc)

            new_meta = dict(meta)
            new_meta["parent_versions"] = [new_parent_version]

            new_child_version = self.store.create_version(
                tenant_id=tenant_id,
                name=child["name"],
                constraints=new_child_constraints,
                metadata=new_meta,
            )
            updated_children[child["name"]] = new_child_version

            # Supersede old relationship
            for rel_id, rel in tree.relationships.items():
                if rel.child_version == cv:
                    tree.supersede_relationship(rel_id, new_child_version)

            new_rel = ConstraintInheritanceRelationship(
                child_version=new_child_version,
                parent_versions=[new_parent_version],
                overrides=child_overrides,
                created_by=updated_by,
            )
            tree.add_relationship(new_rel)

        return updated_children

    def get_constraint_source(
        self, tenant_id: str, version: int, constraint_name: str
    ) -> ConstraintSource:
        cs = self.store.get_constraints(tenant_id, version)
        if not cs:
            return ConstraintSource.UNKNOWN
        meta = cs.get("metadata", {})
        if constraint_name in meta.get("overrides", {}):
            return ConstraintSource.OVERRIDDEN
        if constraint_name in meta.get("own_constraints", {}):
            return ConstraintSource.OWN
        if constraint_name in meta.get("inherited_constraints", {}):
            return ConstraintSource.INHERITED
        return ConstraintSource.OWN

    def get_inheritance_tree(self, tenant_id: str) -> Optional[ConstraintInheritanceTree]:
        return self.trees.get(tenant_id)

    def _merge_parents(self, parent_sets: List[dict]) -> List[dict]:
        merged: Dict[str, dict] = {}
        conflicts: Dict[str, dict] = {}
        for ps in parent_sets:
            for c in ps.get("canonical_constraints", []):
                cname = c.get("identity_string", "")
                if cname in merged:
                    existing = merged[cname]
                    if existing.get("canonical_form") != c.get("canonical_form"):
                        conflicts[cname] = {
                            "parent1": existing.get("canonical_form"),
                            "parent2": c.get("canonical_form"),
                        }
                else:
                    merged[cname] = dict(c)
        if conflicts:
            raise ValueError(f"Multiple inheritance conflicts: {json.dumps(conflicts)}")
        return list(merged.values())


