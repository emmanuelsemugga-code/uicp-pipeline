#!/usr/bin/env python3
"""
app/api.py — GAP-22 REST API Gateway
GAP-18 (multi-tenancy), GAP-20 (AuditLog), GAP-19 (ConstraintStore) integrated.
"""
import json, os, uuid, sys
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g

sys.path.insert(0, os.getcwd())

from app.auth import require_api_key, extract_tenant_from_key
from app.logging import log_request_start, log_request_end, extract_error_type
from app.errors import (
    APIError, MissingConstraintSet, MissingBindings, MalformedJSON,
    EnforcementError, ConstraintSetLoadError, GatewayUnavailable, error_response,
)
from engines.phase4_engine import Phase4EnforcementGateway
from engines.phase5_engine import Phase5Engine
from app.constraint_store import LocalFileConstraintStore, PostgreSQLConstraintStore
from app.audit_log import LocalFileAuditLog, PostgreSQLAuditLog

app = Flask(__name__)

# ── Startup ──────────────────────────────────────────────────
@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())[:8]
    log_request_start(g.request_id)

@app.after_request
def after_request(response):
    endpoint = request.endpoint or "unknown"
    error_type = None
    try:
        data = json.loads(response.get_data(as_text=True))
        error_type = extract_error_type(data)
    except Exception:
        pass
    log_request_end(endpoint, response.status_code, error_type)
    return response

def load_encryption_key():
    key_hex = os.environ.get("PERSONAL_DATA_STORE_KEY")
    if not key_hex:
        print("WARNING: PERSONAL_DATA_STORE_KEY not set.")
        return None
    try:
        return bytes.fromhex(key_hex)
    except ValueError:
        raise ValueError("PERSONAL_DATA_STORE_KEY must be a 64-character hex string")

try:
    ENCRYPTION_KEY = load_encryption_key()
    print("Encryption key loaded" if ENCRYPTION_KEY else "Encryption key not set")
except Exception as e:
    print(f"FATAL STARTUP ERROR: {e}")
    exit(1)

# GAP-20: Select audit log backend based on DATABASE_URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    AUDIT_LOG = PostgreSQLAuditLog(DATABASE_URL)
    print("Using PostgreSQL audit log backend")
else:
    AUDIT_LOG = LocalFileAuditLog()
    print("Using local in-memory audit log backend")

# GAP-19: Select constraint store backend
if DATABASE_URL:
    CONSTRAINT_STORE = PostgreSQLConstraintStore(DATABASE_URL)
else:
    base_path = os.environ.get("CONSTRAINT_SET_PATH", "/etc/constraints.json")
    CONSTRAINT_STORE = LocalFileConstraintStore(base_path)

GATEWAY = Phase4EnforcementGateway(audit_log=AUDIT_LOG)
AUDIT = Phase5Engine(last_phase4_hash="init")

# ── Health Check ──────────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

# ── Main Enforcement Endpoint ──────────────────────────────────
@app.route('/enforce', methods=['POST'])
@require_api_key
def enforce():
    try:
        try:
            request_body = request.get_json()
        except Exception as e:
            raise MalformedJSON(str(e))
        if not request_body:
            raise MalformedJSON("Request body is empty")

        output_id = request_body.get("output_id") or str(uuid.uuid4())

        # GAP-18: Determine tenant
        tenant_id = getattr(g, "tenant_id", "default")

        # GAP-19: Load constraints for this tenant via the store
        constraint_set, version = CONSTRAINT_STORE.get_constraints(tenant_id)

        if not constraint_set or "canonical_constraints" not in constraint_set:
            raise ConstraintSetLoadError("Constraint set is empty or malformed")

        # Load constraints into the gateway
        GATEWAY._enforceable = constraint_set["canonical_constraints"]

        bindings = None
        if "bindings" in request_body:
            bindings = request_body["bindings"]
        elif "model_output" in request_body and "binding_schema" in request_body:
            bindings = {}
        else:
            raise MissingBindings()

        decision_request = {
            "output_id": output_id,
            "bindings": bindings,
            "constraint_version": version,
            "tenant_id": tenant_id,
        }
        decision = GATEWAY.check_output(decision_request)
        decision["processed_at"] = datetime.now(timezone.utc).isoformat()

        http_status = 503 if decision["status"] == "GATEWAY_UNAVAILABLE" else 200
        return jsonify(decision), http_status

    except APIError as api_err:
        response, status_code = error_response(api_err, g.request_id)
        return response, status_code
    except Exception:
        response, status_code = error_response(GatewayUnavailable(), g.request_id)
        return response, status_code

# ── Error Handlers ──────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error":True,"error_type":"NOT_FOUND","message":f"Endpoint {request.path} not found","retryable":False,"request_id":g.get("request_id","unknown")}),404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error":True,"error_type":"METHOD_NOT_ALLOWED","message":f"{request.method} not allowed for {request.path}","retryable":False,"request_id":g.get("request_id","unknown")}),405

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
