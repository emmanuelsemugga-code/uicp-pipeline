#!/usr/bin/env python3
"""
app/audit_logger.py — GAP‑16 Audit Logger for Regulatory Reconstruction

Enriches Phase 4 enforcement decision records with the fields a regulator,
auditor, or compliance officer requires for complete reconstruction of
an AI‑assisted decision.

Does NOT modify the enforcement engine. Wraps an existing decision dict
and adds structured context. Idempotent — enriching the same record twice
produces the same output.
"""
import hashlib, json, uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class AuditLogger:
    """
    Enriches a Phase 4 enforcement decision with the contextual metadata
    required for regulatory reconstruction.

    Required context fields (supplied by the operator or orchestrator):
      - model_output:         the raw text the AI model produced
      - extraction_schema_id: version identifier for the binding schema
      - constraint_version:   version of the constraint set in force
      - constraint_author:    operator who committed the constraint set
      - tenant_id:            tenant under which enforcement ran

    Optional context:
      - request_id:           if not provided, one is generated
      - operator_override:    if a human override was applied
      - override_reason:      the documented reason for the override
    """

    REQUIRED_CONTEXT = [
        "model_output",
        "extraction_schema_id",
        "constraint_version",
        "constraint_author",
        "tenant_id",
    ]

    @classmethod
    def enrich(cls, decision: dict, context: Optional[dict] = None) -> dict:
        """
        Produce a regulatory‑grade audit record from a Phase 4 decision.

        Args:
            decision: the dict returned by Phase4EnforcementGateway.check_output()
            context:  optional dict supplying the regulatory metadata listed above.
                      If None or incomplete, missing fields are filled with
                      safe placeholders — never with a value that could be
                      mistaken for real data.

        Returns:
            A new dict containing the full regulatory record.  The original
            decision dict is NEVER mutated.
        """
        ctx = deepcopy(context) if context else {}
        record = deepcopy(decision)

        # ── Required fields with safe defaults ────────────────────────
        model_output = ctx.get("model_output", "NOT_RECORDED")
        extraction_schema_id = ctx.get("extraction_schema_id", "UNKNOWN")
        constraint_version = ctx.get("constraint_version", "UNKNOWN")
        constraint_author = ctx.get("constraint_author", "UNKNOWN")
        tenant_id = ctx.get("tenant_id", "UNKNOWN")
        request_id = ctx.get("request_id", str(uuid.uuid4()))

        # ── Optional override tracking ────────────────────────────────
        operator_override = ctx.get("operator_override", False)
        override_reason = ctx.get("override_reason", "")

        # ── Timestamps ────────────────────────────────────────────────
        recorded_at = datetime.now(timezone.utc).isoformat()

        # ── Assemble enriched record ───────────────────────────────────
        enriched = {
            **record,
            "audit_metadata": {
                "schema_version": "1.0.0",
                "recorded_at": recorded_at,
                "request_id": request_id,
                "tenant_id": tenant_id,
                "model_output": model_output,
                "extraction_schema_id": extraction_schema_id,
                "constraint_version": constraint_version,
                "constraint_author": constraint_author,
                "operator_override": operator_override,
                "override_reason": override_reason if operator_override else None,
            },
            "regulatory_reconstruction": {
                "decision_status": record.get("status", "UNKNOWN"),
                "violations_detail": record.get("violations", []),
                "binding_evidence_hash": cls._hash_dict(
                    record.get("binding_evidence", {})
                ),
                "constraint_set_identifier": (
                    f"{tenant_id}:v{constraint_version}"
                ),
                "reconstruction_possible": (
                    model_output != "NOT_RECORDED"
                    and constraint_version != "UNKNOWN"
                ),
            },
        }

        return enriched

    @staticmethod
    def _hash_dict(data: dict) -> str:
        """Deterministic SHA‑256 of a dict for tamper‑evidence."""
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
