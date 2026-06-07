#!/usr/bin/env python3
"""
app/deployment_manager.py — GAP‑17 Multi‑Stage Constraint Deployment & Canary Rollout
Progressive rollout: canary (1%) → alpha (10%) → beta (50%) → stable (100%).
Hash‑based traffic splitting, metrics collection, automatic rollback on anomaly.
"""
import json, hashlib, time, uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple

# ── Traffic splitting ───────────────────────────────────────
def should_use_new_constraint(request_id: str, traffic_percent: int) -> bool:
    """Deterministic hash‑based traffic split. Same request_id always gets same decision."""
    h = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
    return (h % 100) < traffic_percent


# ── Data structures ─────────────────────────────────────────
class DeploymentStage:
    def __init__(self, name: str, traffic_percent: int, duration_seconds: int,
                 auto_advance: bool = True):
        self.name = name
        self.traffic_percent = traffic_percent
        self.duration_seconds = duration_seconds
        self.auto_advance = auto_advance


class DeploymentConfig:
    def __init__(self, tenant_id: str, target_version: int,
                 reason: str, created_by: str,
                 scheduled_at: Optional[str] = None):
        self.tenant_id = tenant_id
        self.target_version = target_version
        self.reason = reason
        self.created_by = created_by
        self.scheduled_at = scheduled_at
        self.stages = [
            DeploymentStage("canary", 1, 300, auto_advance=True),
            DeploymentStage("alpha", 10, 600, auto_advance=False),
            DeploymentStage("beta", 50, 900, auto_advance=False),
            DeploymentStage("stable", 100, 0, auto_advance=False),
        ]
        self.rollback_triggers = {
            "approval_rate_drop": 0.05,
            "error_rate_threshold": 0.01,
        }

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "target_version": self.target_version,
            "reason": self.reason,
            "created_by": self.created_by,
            "scheduled_at": self.scheduled_at,
            "stages": [{"name": s.name, "traffic_percent": s.traffic_percent,
                        "duration_seconds": s.duration_seconds,
                        "auto_advance": s.auto_advance} for s in self.stages],
        }


class DeploymentState:
    VALID_STATES = ["CREATED", "CANARY_DEPLOYING", "CANARY_SUCCEEDED",
                    "ALPHA_DEPLOYING", "ALPHA_SUCCEEDED",
                    "BETA_DEPLOYING", "BETA_SUCCEEDED",
                    "STABLE_DEPLOYING", "COMPLETED",
                    "ROLLED_BACK", "PAUSED", "FAILED"]

    def __init__(self, deployment_id: str, config: DeploymentConfig):
        self.deployment_id = deployment_id
        self.config = config
        self.status = "CREATED"
        self.current_stage_index = -1
        self.traffic_percent = 0
        self.stage_started_at: Optional[str] = None
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.rollback_reason: Optional[str] = None
        self.rollback_at: Optional[str] = None

    @property
    def current_stage_name(self) -> str:
        if self.current_stage_index < 0:
            return "pending"
        return self.config.stages[self.current_stage_index].name

    @property
    def is_active(self) -> bool:
        return self.status.endswith("_DEPLOYING")

    def to_dict(self) -> dict:
        return {
            "deployment_id": self.deployment_id,
            "status": self.status,
            "current_stage": self.current_stage_name,
            "traffic_percent": self.traffic_percent,
            "stage_started_at": self.stage_started_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "rollback_reason": self.rollback_reason,
            "config": self.config.to_dict(),
        }


# ── Metrics collector ───────────────────────────────────────
class MetricsCollector:
    def __init__(self):
        self._metrics: List[dict] = []

    def record(self, deployment_id: str, stage: str, decision: str,
               error: Optional[str], latency_ms: float,
               request_id: str, timestamp: Optional[str] = None):
        self._metrics.append({
            "deployment_id": deployment_id,
            "stage": stage,
            "decision": decision,
            "error": error,
            "latency_ms": latency_ms,
            "request_id": request_id,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        })

    def get_stage_metrics(self, deployment_id: str, stage: str,
                          minutes: int = 5) -> List[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [m for m in self._metrics
                if m["deployment_id"] == deployment_id
                and m["stage"] == stage
                and m["timestamp"] >= cutoff.isoformat()]

    def get_baseline(self, tenant_id: str, hours: int = 1) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        baseline = [m for m in self._metrics
                    if m.get("tenant_id") == tenant_id
                    and m.get("stage") == "stable"
                    and m["timestamp"] >= cutoff.isoformat()]
        if not baseline:
            return {"approval_rate": 0.90, "error_rate": 0.001}
        total = len(baseline)
        approvals = sum(1 for m in baseline if m["decision"] == "ALLOW")
        errors = sum(1 for m in baseline if m["error"])
        return {
            "approval_rate": approvals / total if total else 0.90,
            "error_rate": errors / total if total else 0.001,
        }

    def analyze_stage(self, deployment_id: str, stage: str,
                      baseline: dict, config: DeploymentConfig) -> dict:
        recent = self.get_stage_metrics(deployment_id, stage, minutes=5)
        if not recent:
            return {"should_advance": False, "should_rollback": False,
                    "anomalies": [], "message": "No metrics yet"}

        total = len(recent)
        approvals = sum(1 for m in recent if m["decision"] == "ALLOW")
        errors = sum(1 for m in recent if m["error"])
        approval_rate = approvals / total if total else 0
        error_rate = errors / total if total else 0

        triggers = config.rollback_triggers
        anomalies = []

        approval_drop = baseline["approval_rate"] - approval_rate
        if approval_drop > triggers.get("approval_rate_drop", 0.05):
            anomalies.append(f"approval_rate_drop:{approval_drop:.2%}")

        if error_rate > triggers.get("error_rate_threshold", 0.01):
            anomalies.append(f"error_spike:{error_rate:.2%}")

        return {
            "approval_rate": approval_rate,
            "error_rate": error_rate,
            "baseline_approval_rate": baseline["approval_rate"],
            "approval_rate_change": approval_drop,
            "anomalies": anomalies,
            "should_rollback": bool(anomalies),
            "should_advance": not anomalies,
            "message": "OK" if not anomalies else f"Anomalies: {', '.join(anomalies)}",
        }


# ── Deployment manager ──────────────────────────────────────
class DeploymentManager:
    def __init__(self, metrics: MetricsCollector = None):
        self._deployments: Dict[str, DeploymentState] = {}
        self._metrics = metrics or MetricsCollector()

    def create_deployment(self, config: DeploymentConfig) -> str:
        dep_id = str(uuid.uuid4())[:8]
        self._deployments[dep_id] = DeploymentState(dep_id, config)
        return dep_id

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentState]:
        return self._deployments.get(deployment_id)

    def get_active_deployment(self, tenant_id: str) -> Optional[DeploymentState]:
        for dep in self._deployments.values():
            if dep.config.tenant_id == tenant_id and dep.is_active:
                return dep
        return None

    def start_deployment(self, deployment_id: str) -> dict:
        dep = self._deployments.get(deployment_id)
        if not dep:
            return {"error": "Deployment not found"}
        if dep.config.scheduled_at:
            scheduled = datetime.fromisoformat(dep.config.scheduled_at)
            if datetime.now(timezone.utc) < scheduled:
                return {"error": "Not yet scheduled"}
        dep.current_stage_index = 0
        stage = dep.config.stages[0]
        dep.status = "CANARY_DEPLOYING"
        dep.traffic_percent = stage.traffic_percent
        dep.stage_started_at = datetime.now(timezone.utc).isoformat()
        dep.started_at = dep.stage_started_at
        return {"status": "started", "stage": stage.name}

    def advance_stage(self, deployment_id: str, manual: bool = False) -> dict:
        dep = self._deployments.get(deployment_id)
        if not dep:
            return {"error": "Deployment not found"}
        if dep.current_stage_index < 0:
            return {"error": "Deployment not started"}

        current_stage = dep.config.stages[dep.current_stage_index]
        if not manual and not current_stage.auto_advance:
            return {"error": "Manual approval required for this stage"}

        next_idx = dep.current_stage_index + 1
        if next_idx >= len(dep.config.stages):
            dep.status = "COMPLETED"
            dep.traffic_percent = 100
            dep.completed_at = datetime.now(timezone.utc).isoformat()
            return {"status": "completed"}

        next_stage = dep.config.stages[next_idx]
        dep.current_stage_index = next_idx
        dep.status = f"{next_stage.name.upper()}_DEPLOYING"
        dep.traffic_percent = next_stage.traffic_percent
        dep.stage_started_at = datetime.now(timezone.utc).isoformat()
        return {"status": "advanced", "stage": next_stage.name,
                "traffic_percent": next_stage.traffic_percent}

    def rollback(self, deployment_id: str, reason: str) -> dict:
        dep = self._deployments.get(deployment_id)
        if not dep:
            return {"error": "Deployment not found"}
        dep.status = "ROLLED_BACK"
        dep.traffic_percent = 0
        dep.rollback_reason = reason
        dep.rollback_at = datetime.now(timezone.utc).isoformat()
        return {"status": "rolled_back", "reason": reason}

    def pause(self, deployment_id: str) -> dict:
        dep = self._deployments.get(deployment_id)
        if not dep:
            return {"error": "Deployment not found"}
        dep.status = "PAUSED"
        return {"status": "paused"}

    def check_and_decide(self, deployment_id: str, tenant_id: str) -> dict:
        dep = self._deployments.get(deployment_id)
        if not dep or not dep.is_active:
            return {"action": "none", "reason": "Not active"}

        stage_name = dep.current_stage_name
        baseline = self._metrics.get_baseline(tenant_id)
        analysis = self._metrics.analyze_stage(
            deployment_id, stage_name, baseline, dep.config)

        if analysis["should_rollback"]:
            self.rollback(deployment_id, analysis.get("message", "Anomaly detected"))
            return {"action": "rolled_back", "reason": analysis.get("message")}

        if analysis["should_advance"]:
            current_stage = dep.config.stages[dep.current_stage_index]
            if current_stage.auto_advance:
                result = self.advance_stage(deployment_id, manual=False)
                return {"action": "advanced", "stage": result.get("stage")}

        return {"action": "monitor", "analysis": analysis}
