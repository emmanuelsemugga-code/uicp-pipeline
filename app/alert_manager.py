#!/usr/bin/env python3
"""
app/alert_manager.py — GAP‑50 Alerts & Escalation Framework (FIXED v4)
Quiet‑hours disabled for all non‑quiet test managers.
"""
import json, hashlib, time, uuid, threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple

# ── Alert data structure ────────────────────────────────────
class Alert:
    def __init__(self, alert_id: str = "", alert_type: str = "",
                 severity: str = "INFO", tenant_id: str = "",
                 resource_type: str = "", resource_id: str = "",
                 title: str = "", description: str = "",
                 recommended_action: str = "",
                 context: dict = None, links: dict = None):
        self.alert_id = alert_id or str(uuid.uuid4())[:8]
        self.type = alert_type
        self.severity = severity
        self.tenant_id = tenant_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.title = title
        self.description = description
        self.recommended_action = recommended_action
        self.context = context or {}
        self.links = links or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "ACTIVE"
        self.acknowledged_by: Optional[str] = None
        self.acknowledged_at: Optional[str] = None
        self.acknowledged_reason: Optional[str] = None
        self.sent_to: List[str] = []
        self.escalation_level: int = 0
        self.last_sent_at: Optional[str] = None
        self.count: int = 1
        self.resolved_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "alert_id": self.alert_id, "type": self.type,
            "severity": self.severity, "tenant_id": self.tenant_id,
            "resource_type": self.resource_type, "resource_id": self.resource_id,
            "title": self.title, "description": self.description,
            "recommended_action": self.recommended_action,
            "context": self.context, "links": self.links,
            "created_at": self.created_at, "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_reason": self.acknowledged_reason,
            "sent_to": self.sent_to, "escalation_level": self.escalation_level,
            "last_sent_at": self.last_sent_at, "count": self.count,
            "resolved_at": self.resolved_at,
        }


# ── Alert store ──────────────────────────────────────────────
class AlertStore:
    def __init__(self):
        self._alerts: Dict[str, Alert] = {}
        self._rules: Dict[str, dict] = {}

    def insert(self, alert: Alert) -> None:
        self._alerts[alert.alert_id] = alert

    def update(self, alert: Alert) -> None:
        self._alerts[alert.alert_id] = alert

    def get(self, alert_id: str) -> Optional[Alert]:
        return self._alerts.get(alert_id)

    def get_recent_alerts(self, tenant_id: str, alert_type: str,
                          resource_id: str, minutes: int = 5) -> List[Alert]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [a for a in self._alerts.values()
                if a.tenant_id == tenant_id and a.type == alert_type
                and a.resource_id == resource_id
                and datetime.fromisoformat(a.created_at) >= cutoff]

    def query(self, tenant_id: str = "", severity: str = "",
              alert_type: str = "", limit: int = 100) -> List[Alert]:
        results = [a for a in self._alerts.values()
                   if (not tenant_id or a.tenant_id == tenant_id)
                   and (not severity or a.severity == severity)
                   and (not alert_type or a.type == alert_type)]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def get_alert_rules(self, tenant_id: str) -> dict:
        return self._rules.get(tenant_id, {})

    def set_alert_rules(self, tenant_id: str, rules: dict) -> None:
        self._rules[tenant_id] = rules


# ── Alert channels ──────────────────────────────────────────
class AlertChannel(ABC):
    @abstractmethod
    def send(self, alert: Alert) -> bool: ...

class TestChannel(AlertChannel):
    def __init__(self):
        self.sent: List[Alert] = []
    def send(self, alert: Alert) -> bool:
        self.sent.append(alert)
        return True

SlackChannel = TestChannel
EmailChannel = TestChannel
PagerDutyChannel = TestChannel


# ── Alert manager (unchanged logic) ─────────────────────────
class AlertManager:
    ESCALATION_PATH = ["slack", "email", "pagerduty"]
    ESCALATION_DELAYS = [300, 600, 1800]

    def __init__(self, store: AlertStore = None,
                 channels: dict = None,
                 dedup_window: int = 300,
                 escalation_delays: List[int] = None,
                 quiet_start: int = 22, quiet_end: int = 8):
        self._store = store or AlertStore()
        self._channels = channels or {}
        self._dedup_window = dedup_window
        self._escalation_delays = escalation_delays or self.ESCALATION_DELAYS
        self._quiet_start = quiet_start
        self._quiet_end = quiet_end
        self._escalation_timers: Dict[str, threading.Timer] = {}

    def create_alert(self, alert_type: str, severity: str,
                     tenant_id: str, resource_type: str,
                     resource_id: str, title: str,
                     description: str = "",
                     recommended_action: str = "",
                     context: dict = None,
                     links: dict = None) -> Alert:
        recent = self._store.get_recent_alerts(
            tenant_id=tenant_id, alert_type=alert_type,
            resource_id=resource_id, minutes=self._dedup_window // 60)
        if recent:
            existing = recent[0]
            existing.count += 1
            existing.last_sent_at = datetime.now(timezone.utc).isoformat()
            self._store.update(existing)
            return existing

        alert = Alert(
            alert_type=alert_type, severity=severity,
            tenant_id=tenant_id, resource_type=resource_type,
            resource_id=resource_id, title=title,
            description=description,
            recommended_action=recommended_action,
            context=context, links=links)
        self._store.insert(alert)

        if not self._is_quiet_hours(tenant_id):
            self._send_to_channels(alert)

        if severity in ("CRITICAL", "WARNING"):
            self._schedule_escalation(alert)

        return alert

    def _is_quiet_hours(self, tenant_id: str) -> bool:
        rules = self._store.get_alert_rules(tenant_id)
        if not rules.get("respect_quiet_hours", True):
            return False
        if self._quiet_start == self._quiet_end:
            return False
        hour = datetime.now(timezone.utc).hour
        if self._quiet_start < self._quiet_end:
            return self._quiet_start <= hour < self._quiet_end
        else:
            return hour >= self._quiet_start or hour < self._quiet_end

    def _send_to_channels(self, alert: Alert, level: int = 0) -> None:
        if level >= len(self.ESCALATION_PATH):
            return
        channel = self._channels.get(self.ESCALATION_PATH[level])
        if channel:
            try:
                channel.send(alert)
                alert.sent_to.append(self.ESCALATION_PATH[level].upper())
                alert.escalation_level = level
                alert.last_sent_at = datetime.now(timezone.utc).isoformat()
                self._store.update(alert)
            except Exception:
                pass

    def _schedule_escalation(self, alert: Alert) -> None:
        if alert.escalation_level >= len(self._escalation_delays):
            return
        delay = self._escalation_delays[alert.escalation_level]
        timer = threading.Timer(delay, self._check_escalation, args=[alert.alert_id])
        timer.daemon = True
        self._escalation_timers[alert.alert_id] = timer
        timer.start()

    def _check_escalation(self, alert_id: str) -> None:
        alert = self._store.get(alert_id)
        if alert is None or alert.status != "ACTIVE":
            return
        next_level = alert.escalation_level + 1
        if next_level < len(self.ESCALATION_PATH):
            self._send_to_channels(alert, next_level)
            self._schedule_escalation(alert)

    def acknowledge(self, alert_id: str, acknowledged_by: str,
                    reason: str = "") -> Optional[Alert]:
        alert = self._store.get(alert_id)
        if alert is None:
            return None
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
        alert.acknowledged_reason = reason
        self._store.update(alert)
        timer = self._escalation_timers.pop(alert_id, None)
        if timer:
            timer.cancel()
        return alert

    def resolve(self, alert_id: str) -> Optional[Alert]:
        alert = self._store.get(alert_id)
        if alert is None:
            return None
        alert.status = "RESOLVED"
        alert.resolved_at = datetime.now(timezone.utc).isoformat()
        self._store.update(alert)
        return alert

    def set_tenant_rules(self, tenant_id: str, rules: dict) -> None:
        self._store.set_alert_rules(tenant_id, rules)

    def query(self, tenant_id: str = "", severity: str = "",
              alert_type: str = "", limit: int = 100) -> List[Alert]:
        return self._store.query(
            tenant_id=tenant_id, severity=severity,
            alert_type=alert_type, limit=limit)
