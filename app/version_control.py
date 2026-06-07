#!/usr/bin/env python3
"""
app/version_control.py — GAP‑15 Constraint Version Control & Rollback
Safe rollback operations, version diffing, tagging, and approval workflow.
Works with LocalVersionStore (Colab) or PostgreSQLVersionStore (production).
"""
import json, hashlib, time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict

# ── Data structures ──────────────────────────────────────────
class RollbackResult:
    def __init__(self, status: str, request_id: str = "", version: int = 0,
                 errors: list = None, preview: dict = None):
        self.status = status          # "completed" | "pending_approval" | "rejected" | "failed"
        self.request_id = request_id
        self.version = version
        self.errors = errors or []
        self.preview = preview or {}

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "request_id": self.request_id,
            "version": self.version,
            "errors": self.errors,
            "preview": self.preview,
        }


# ── Abstract version store ───────────────────────────────────
class VersionStore(ABC):
    @abstractmethod
    def create_version(self, tenant_id: str, constraints: dict, metadata: dict) -> int:
        """Create a new version. Returns version number."""
        ...
    @abstractmethod
    def get_version(self, tenant_id: str, version: int) -> Optional[dict]:
        """Get full version record (content + metadata)."""
        ...
    @abstractmethod
    def get_active_version(self, tenant_id: str) -> Optional[dict]:
        """Get the currently active version record."""
        ...
    @abstractmethod
    def list_versions(self, tenant_id: str, tag: str = None,
                      created_by: str = None, limit: int = 50) -> List[dict]:
        """List versions with optional filters."""
        ...
    @abstractmethod
    def activate_version(self, tenant_id: str, version: int) -> None:
        """Mark a version as active (and deactivate others)."""
        ...
    @abstractmethod
    def add_tag(self, tenant_id: str, version: int, tag: str) -> None:
        """Add a tag to a version."""
        ...


# ── Local (Colab) version store ─────────────────────────────
class LocalVersionStore(VersionStore):
    def __init__(self):
        self._tenants: Dict[str, list] = {}   # tenant_id → list of version records

    def create_version(self, tenant_id: str, constraints: dict, metadata: dict) -> int:
        if tenant_id not in self._tenants:
            self._tenants[tenant_id] = []
        version = len(self._tenants[tenant_id]) + 1
        content_hash = hashlib.sha256(
            json.dumps(constraints, sort_keys=True).encode()
        ).hexdigest()
        record = {
            "version": version,
            "content": constraints,
            "content_hash": content_hash,
            "active": False,
            "change_type": metadata.get("change_type", "update"),
            "change_summary": metadata.get("change_summary", ""),
            "change_details": metadata.get("change_details", {}),
            "created_at": metadata.get("created_at", datetime.now(timezone.utc).isoformat()),
            "created_by": metadata.get("created_by", "unknown"),
            "tags": metadata.get("tags", []),
            "created_from_version": metadata.get("created_from_version"),
            "rollback_reason": metadata.get("rollback_reason"),
            "rollback_approved_by": metadata.get("rollback_approved_by"),
            "validation_status": metadata.get("validation_status", "unchecked"),
        }
        self._tenants[tenant_id].append(record)
        return version

    def get_version(self, tenant_id: str, version: int) -> Optional[dict]:
        versions = self._tenants.get(tenant_id, [])
        for v in versions:
            if v["version"] == version:
                return dict(v)
        return None

    def get_active_version(self, tenant_id: str) -> Optional[dict]:
        versions = self._tenants.get(tenant_id, [])
        for v in reversed(versions):
            if v["active"]:
                return dict(v)
        return None

    def list_versions(self, tenant_id: str, tag: str = None,
                      created_by: str = None, limit: int = 50) -> List[dict]:
        versions = self._tenants.get(tenant_id, [])
        result = []
        for v in reversed(versions):
            if tag and tag not in v.get("tags", []):
                continue
            if created_by and v.get("created_by") != created_by:
                continue
            result.append(dict(v))
            if len(result) >= limit:
                break
        return result

    def activate_version(self, tenant_id: str, version: int) -> None:
        versions = self._tenants.get(tenant_id, [])
        for v in versions:
            v["active"] = (v["version"] == version)

    def add_tag(self, tenant_id: str, version: int, tag: str) -> None:
        v = self.get_version(tenant_id, version)
        if v:
            tags = list(v.get("tags", []))
            if tag not in tags:
                tags.append(tag)
            self._update_field(tenant_id, version, "tags", tags)

    def _update_field(self, tenant_id: str, version: int, field: str, value):
        versions = self._tenants.get(tenant_id, [])
        for v in versions:
            if v["version"] == version:
                v[field] = value
                return


# ── Version Diff Generator ───────────────────────────────────
class VersionDiffGenerator:
    @staticmethod
    def diff(v_a: Optional[dict], v_b: Optional[dict]) -> dict:
        if not v_a or not v_b:
            return {"added": [], "removed": [], "modified": [], "unchanged": []}
        ca = v_a.get("content", {}).get("canonical_constraints", [])
        cb = v_b.get("content", {}).get("canonical_constraints", [])
        map_a = {c["identity_string"]: c for c in ca if isinstance(c, dict)}
        map_b = {c["identity_string"]: c for c in cb if isinstance(c, dict)}
        added = [c for name, c in map_b.items() if name not in map_a]
        removed = [c for name, c in map_a.items() if name not in map_b]
        modified = []
        unchanged = []
        for name in map_a:
            if name in map_b:
                if map_a[name] != map_b[name]:
                    modified.append({"identity_string": name,
                                     "old_form": map_a[name].get("canonical_form", ""),
                                     "new_form": map_b[name].get("canonical_form", "")})
                else:
                    unchanged.append(map_a[name])
        return {"added": added, "removed": removed,
                "modified": modified, "unchanged": unchanged}


# ── Approval Manager ─────────────────────────────────────────
class ApprovalManager:
    def __init__(self):
        self._requests: Dict[str, dict] = {}

    def create_request(self, tenant_id: str, target_version: int,
                       reason: str, requesting_user: str,
                       approvers_needed: int = 2) -> str:
        import uuid
        req_id = str(uuid.uuid4())[:8]
        self._requests[req_id] = {
            "request_id": req_id,
            "tenant_id": tenant_id,
            "target_version": target_version,
            "reason": reason,
            "requesting_user": requesting_user,
            "approvers_needed": approvers_needed,
            "approvals": [],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return req_id

    def approve(self, request_id: str, approver: str) -> dict:
        req = self._requests.get(request_id)
        if not req:
            return {"status": "not_found"}
        if approver not in req["approvals"]:
            req["approvals"].append(approver)
        if len(req["approvals"]) >= req["approvers_needed"]:
            req["status"] = "approved"
            return {"status": "approved", "approvals": req["approvals"]}
        return {"status": "pending", "approvals": req["approvals"]}

    def get_request(self, request_id: str) -> Optional[dict]:
        return self._requests.get(request_id)


# ── Main Version Controller ──────────────────────────────────
class VersionController:
    def __init__(self, store: VersionStore,
                 approval_manager: ApprovalManager = None):
        self._store = store
        self._diff = VersionDiffGenerator()
        self._approval = approval_manager or ApprovalManager()

    def create_version(self, tenant_id: str, constraints: dict,
                       change_type: str, change_summary: str,
                       created_by: str, tags: list = None,
                       change_details: dict = None) -> int:
        metadata = {
            "change_type": change_type,
            "change_summary": change_summary,
            "created_by": created_by,
            "change_details": change_details or {},
            "tags": tags or [],
            "validation_status": "unchecked",
        }
        return self._store.create_version(tenant_id, constraints, metadata)

    def get_version(self, tenant_id: str, version: int) -> Optional[dict]:
        return self._store.get_version(tenant_id, version)

    def get_active_version(self, tenant_id: str) -> Optional[dict]:
        return self._store.get_active_version(tenant_id)

    def list_versions(self, tenant_id: str, tag: str = None,
                      created_by: str = None, limit: int = 50) -> List[dict]:
        return self._store.list_versions(tenant_id, tag=tag,
                                         created_by=created_by, limit=limit)

    def diff_versions(self, tenant_id: str, v_a: int, v_b: int) -> dict:
        a = self._store.get_version(tenant_id, v_a)
        b = self._store.get_version(tenant_id, v_b)
        return self._diff.diff(a, b)

    def rollback(self, tenant_id: str, target_version: int,
                 reason: str, requesting_user: str,
                 require_approval: bool = True) -> RollbackResult:
        target = self._store.get_version(tenant_id, target_version)
        if not target:
            return RollbackResult("failed", errors=[f"Version {target_version} not found"])
        active = self._store.get_active_version(tenant_id)
        if active and active["version"] == target_version:
            return RollbackResult("failed", errors=["Target version is already active"])
        preview = self.diff_versions(tenant_id,
                                     active["version"] if active else 0, target_version)

        if require_approval:
            req_id = self._approval.create_request(
                tenant_id, target_version, reason, requesting_user)
            return RollbackResult("pending_approval", request_id=req_id,
                                  version=target_version, preview=preview)

        # Auto‑approve
        metadata = {
            "change_type": "rollback",
            "change_summary": f"Rollback to v{target_version}: {reason}",
            "created_by": requesting_user,
            "created_from_version": target_version,
            "rollback_reason": reason,
            "rollback_approved_by": requesting_user,
            "validation_status": target.get("validation_status", "unchecked"),
        }
        new_version = self._store.create_version(tenant_id, target["content"], metadata)
        self._store.activate_version(tenant_id, new_version)
        return RollbackResult("completed", version=new_version, preview=preview)

    def approve_rollback(self, request_id: str, approver: str) -> RollbackResult:
        result = self._approval.approve(request_id, approver)
        if result["status"] == "approved":
            req = self._approval.get_request(request_id)
            target = self._store.get_version(req["tenant_id"], req["target_version"])
            metadata = {
                "change_type": "rollback",
                "change_summary": f"Rollback to v{req['target_version']}: {req['reason']}",
                "created_by": req["requesting_user"],
                "created_from_version": req["target_version"],
                "rollback_reason": req["reason"],
                "rollback_approved_by": ", ".join(result["approvals"]),
                "validation_status": target.get("validation_status", "unchecked") if target else "unchecked",
            }
            new_version = self._store.create_version(
                req["tenant_id"], target["content"], metadata)
            self._store.activate_version(req["tenant_id"], new_version)
            return RollbackResult("completed", version=new_version)
        return RollbackResult("pending_approval", request_id=request_id)

    def tag_version(self, tenant_id: str, version: int, tag: str) -> None:
        self._store.add_tag(tenant_id, version, tag)
