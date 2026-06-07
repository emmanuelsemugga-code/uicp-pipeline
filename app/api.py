#!/usr/bin/env python3
"""
app/api.py — GAP-22 REST API Gateway

Main Flask application exposing the UICP enforcement gateway over HTTP.

Endpoints:
  POST /enforce  — Run enforcement (main endpoint)
  GET /health    — Health check for Docker/Kubernetes

Environment variables:
  API_KEY                   — X-API-Key for authentication
  CONSTRAINT_SET_PATH       — Path to constraint set JSON file
  PERSONAL_DATA_STORE_KEY   — AES-256 encryption key (hex string, optional)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g

from app.auth import require_api_key, get_api_key_from_env, mask_api_key
from app.logging import log_request_start, log_request_end, extract_error_type
from app.errors import (
    APIError, MissingConstraintSet, MissingBindings, MalformedJSON,
    EnforcementError, EncryptionKeyUnavailable, ConstraintSetLoadError,
    GatewayUnavailable, error_response,
)

# Import the enforcement engines
import sys
sys.path.insert(0, os.getcwd())

from engines.phase4_engine import Phase4EnforcementGateway
from engines.phase5_engine import Phase5Engine
from extraction.binding_extraction import extract_bindings, GovernedSchema
from export.personal_data_store import EncryptedPersonalDataStore


app = Flask(__name__)


# ── Application startup ──────────────────────────────────────────────────────

@app.before_request
def before_request():
    """
    Called before every request.
    Generate request_id for tracing.
    Log request start.
    """
    g.request_id = str(uuid.uuid4())[:8]
    log_request_start(g.request_id)


@app.after_request
def after_request(response):
    """
    Called after every request.
    Log response.
    """
    endpoint = request.endpoint or "unknown"
    status_code = response.status_code
    error_type = None

    try:
        data = json.loads(response.get_data(as_text=True))
        error_type = extract_error_type(data)
    except Exception:
        pass

    log_request_end(endpoint, status_code, error_type)
    return response


def load_constraint_set():
    """
    Load constraint set from file path in environment variable.
    Fail fast if file not found or invalid JSON.
    """
    constraint_set_path = os.environ.get("CONSTRAINT_SET_PATH")
    if not constraint_set_path:
        raise ValueError(
            "FATAL: CONSTRAINT_SET_PATH environment variable not set. "
            "Example: export CONSTRAINT_SET_PATH='/etc/constraint_set.json'"
        )

    if not os.path.exists(constraint_set_path):
        raise FileNotFoundError(
            f"Constraint set file not found: {constraint_set_path}"
        )

    try:
        with open(constraint_set_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Constraint set file is not valid JSON: {e}"
        )


def load_encryption_key():
    """
    Load encryption key for personal data store.
    Key is 64-char hex string (32 bytes).
    Optional — if not provided, personal data store will not be encrypted.
    """
    key_hex = os.environ.get("PERSONAL_DATA_STORE_KEY")
    if not key_hex:
        print("WARNING: PERSONAL_DATA_STORE_KEY not set. Personal data will not be encrypted.")
        return None

    try:
        return bytes.fromhex(key_hex)
    except ValueError:
        raise ValueError(
            "PERSONAL_DATA_STORE_KEY must be a 64-character hex string (32 bytes)"
        )


# Load at startup
try:
    CONSTRAINT_SET = load_constraint_set()
    ENCRYPTION_KEY = load_encryption_key()
    API_KEY = get_api_key_from_env()
    print("✓ Constraint set loaded")
    print("✓ Encryption key loaded" if ENCRYPTION_KEY else "⚠ Encryption key not set")
    print("✓ API key configured")
except Exception as e:
    print(f"FATAL STARTUP ERROR: {e}")
    exit(1)

# ═══════════════════════════════════════════════════════════════
# GAP‑20: Select audit log backend based on DATABASE_URL env var
# ═══════════════════════════════════════════════════════════════
from app.audit_log import LocalFileAuditLog, PostgreSQLAuditLog

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    AUDIT_LOG = PostgreSQLAuditLog(DATABASE_URL)
    print("✓ Using PostgreSQL audit log backend")
else:
    AUDIT_LOG = LocalFileAuditLog()
    print("✓ Using local in‑memory audit log backend")

GATEWAY = Phase4EnforcementGateway(audit_log=AUDIT_LOG)
AUDIT = Phase5Engine(last_phase4_hash="init")
PERSONAL_DATA_STORE = (
    EncryptedPersonalDataStore(
        store_path="./personal_data_store.enc",
        encryption_key=ENCRYPTION_KEY,
        access_log_path="./personal_data_access.log",
        role="gateway",
    ) if ENCRYPTION_KEY else None
  )


# ── Health Check Endpoint ────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    """
    GET /health
    Health check endpoint for Docker/Kubernetes liveness probes.
    Returns 200 OK if gateway is running.
    """
    return jsonify({"status": "healthy"}), 200


# ── Main Enforcement Endpoint ────────────────────────────────────────────────

@app.route('/enforce', methods=['POST'])
@require_api_key
def enforce():
    """
    POST /enforce

    Main enforcement endpoint. Accepts two modes:

    Mode 1: Raw Model Output
    {
      "model_output": "...",
      "binding_schema": { ... },
      "constraint_set": { ... },
      "output_id": "optional"
    }

    Mode 2: Pre-Extracted Bindings
    {
      "bindings": {"age": 35, "risk": 8},
      "constraint_set": { ... },
      "output_id": "optional"
    }

    Returns decision dict with HTTP 200 (ALLOW/BLOCK) or 503 (GATEWAY_UNAVAILABLE).
    """
    try:
        # ── Parse request body ──────────────────────────────────────────────
        try:
            request_body = request.get_json()
        except Exception as e:
            raise MalformedJSON(str(e))

        if not request_body:
            raise MalformedJSON("Request body is empty")

        # ── Generate or use provided output_id ───────────────────────────────
        output_id = request_body.get("output_id")
        if not output_id:
            output_id = str(uuid.uuid4())

        # ── Load constraint set (either from request or use default) ─────────
        constraint_set = request_body.get("constraint_set")
        if not constraint_set:
            constraint_set = CONSTRAINT_SET

        # ── Determine request mode ──────────────────────────────────────────
        mode = None
        bindings = None

        if "bindings" in request_body:
            # Mode 2: Pre-extracted bindings
            mode = "pre_extracted"
            bindings = request_body["bindings"]
            if not isinstance(bindings, dict):
                raise MissingBindings()

        elif "model_output" in request_body and "binding_schema" in request_body:
            # Mode 1: Raw model output
            mode = "raw_output"
            model_output = request_body["model_output"]
            binding_schema = request_body["binding_schema"]

            if not isinstance(model_output, str):
                raise MalformedJSON("model_output must be a string")
            if not isinstance(binding_schema, dict):
                raise MalformedJSON("binding_schema must be a dict")

            # Extract bindings from model output
            try:
                extraction_result = extract_bindings(
                    model_output, binding_schema, PERSONAL_DATA_STORE
                )
                if extraction_result["status"] == "INCOMPLETE":
                    # Missing variables — proceed with what we have
                    bindings = extraction_result["bindings"]
                else:
                    bindings = extraction_result["bindings"]
            except Exception as e:
                raise EnforcementError(f"Binding extraction failed: {e}")

        else:
            raise MissingBindings()

        # ── Run enforcement ────────────────────────────────────────────────
        decision_request = {
            "output_id": output_id,
            "bindings": bindings,
        }

        decision = GATEWAY.check_output(decision_request)

        # ── Add metadata ───────────────────────────────────────────────────
        decision["request_mode"] = mode
        decision["processed_at"] = datetime.now(timezone.utc).isoformat()

        # ── Determine HTTP status code from decision status ─────────────────
        http_status = 200
        if decision["status"] == "GATEWAY_UNAVAILABLE":
            http_status = 503
        elif decision["status"] == "BLOCK":
            http_status = 200  # BLOCK is a valid decision, not an error

        return jsonify(decision), http_status

    except APIError as api_err:
        response, status_code = error_response(api_err, g.request_id)
        return response, status_code

    except Exception as exc:
        # Catch-all for unexpected errors
        response, status_code = error_response(GatewayUnavailable(), g.request_id)
        return response, status_code


# ── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    """404 Not Found"""
    return jsonify({
        "error": True,
        "error_type": "NOT_FOUND",
        "message": f"Endpoint {request.path} does not exist",
        "retryable": False,
        "request_id": g.get("request_id", "unknown"),
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    """405 Method Not Allowed"""
    return jsonify({
        "error": True,
        "error_type": "METHOD_NOT_ALLOWED",
        "message": f"Method {request.method} not allowed for {request.path}",
        "retryable": False,
        "request_id": g.get("request_id", "unknown"),
    }), 405


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
  
