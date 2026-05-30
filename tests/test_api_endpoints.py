#!/usr/bin/env python3
"""
tests/test_api_endpoints.py — GAP-22 API Endpoint Tests

Tests for the Flask REST API:
- Endpoint routing
- Authentication
- Request modes (raw output vs pre-extracted bindings)
- Error handling
- Health check
- Response format
"""

import sys
import json
import uuid
sys.path.insert(0, '.')

from app.api import app, CONSTRAINT_SET


def test_api_endpoints():
    """Run all API endpoint tests."""
    
    passed = failed = 0

    def chk(label, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  API | {label}")
        else:
            failed += 1
            print(f"  FAIL  API | {label}" + (f" — {detail}" if detail else ""))

    print("\n=== GAP-22 REST API Endpoint Tests ===\n")

    client = app.test_client()
    api_key = "sk-test-abc123"
    
    # Override API_KEY for testing
    import os
    os.environ["API_KEY"] = api_key

    # ── 1. Health check endpoint ────────────────────────────────────────────
    response = client.get('/health')
    chk("GET /health returns 200",
        response.status_code == 200)
    chk("GET /health response is JSON",
        response.json is not None)
    chk("Health response has status field",
        response.json.get("status") == "healthy")

    # ── 2. POST /enforce with raw model output mode ─────────────────────────
    request_body = {
        "model_output": "Loan for client age: 35. Risk score: 8. APPROVE.",
        "binding_schema": {
            "age": {"method": "regex", "pattern": r"age[=: ]*(?P<value>\d+)"},
            "risk": {"method": "regex", "pattern": r"risk[=: ]*(?P<value>\d+)"},
        },
        "constraint_set": {
            "objective_id": "TEST_1",
            "constraints": ["age >= 18", "risk <= 25"],
        },
    }

    response = client.post(
        '/enforce',
        data=json.dumps(request_body),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("POST /enforce (raw mode) returns 200",
        response.status_code == 200)
    chk("POST /enforce response has decision dict",
        response.json is not None and "status" in response.json)
    chk("Decision has output_id",
        response.json.get("output_id") is not None)
    chk("Decision has decision_id",
        response.json.get("decision_id") is not None)
    chk("Decision has timestamp",
        response.json.get("timestamp") is not None)

    # ── 3. POST /enforce with pre-extracted bindings mode ────────────────────
    request_body_bindings = {
        "bindings": {"age": 35, "risk": 8},
        "constraint_set": {
            "objective_id": "TEST_2",
            "constraints": ["age >= 18", "risk <= 25"],
        },
    }

    response = client.post(
        '/enforce',
        data=json.dumps(request_body_bindings),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("POST /enforce (bindings mode) returns 200",
        response.status_code == 200)
    chk("Bindings mode response has decision dict",
        response.json is not None and "status" in response.json)

    # ── 4. Auto-generated output_id ─────────────────────────────────────────
    output_id_from_response = response.json.get("output_id")
    chk("output_id is auto-generated if omitted",
        output_id_from_response is not None and len(output_id_from_response) > 0)

    # ── 5. Client-provided output_id is preserved ───────────────────────────
    request_with_id = dict(request_body_bindings)
    request_with_id["output_id"] = "custom-id-12345"

    response = client.post(
        '/enforce',
        data=json.dumps(request_with_id),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Client-provided output_id is preserved",
        response.json.get("output_id") == "custom-id-12345")

    # ── 6. Missing API key returns 401 ──────────────────────────────────────
    response = client.post(
        '/enforce',
        data=json.dumps(request_body_bindings),
        content_type='application/json',
    )

    chk("Missing X-API-Key returns 401",
        response.status_code == 401)
    chk("Missing key error response has error_type",
        response.json.get("error_type") == "MISSING_API_KEY")
    chk("Error response has retryable flag",
        response.json.get("retryable") is not None)

    # ── 7. Invalid API key returns 401 ──────────────────────────────────────
    response = client.post(
        '/enforce',
        data=json.dumps(request_body_bindings),
        content_type='application/json',
        headers={'X-API-Key': 'wrong-key'},
    )

    chk("Invalid X-API-Key returns 401",
        response.status_code == 401)
    chk("Invalid key error type is INVALID_API_KEY",
        response.json.get("error_type") == "INVALID_API_KEY")

    # ── 8. Missing constraint_set returns 400 ───────────────────────────────
    bad_request = {
        "bindings": {"age": 35, "risk": 8},
        # missing constraint_set
    }

    response = client.post(
        '/enforce',
        data=json.dumps(bad_request),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Missing constraint_set returns 400",
        response.status_code == 400)
    chk("Missing constraint_set error type is correct",
        response.json.get("error_type") == "MISSING_CONSTRAINT_SET")
    chk("400 error not retryable",
        response.json.get("retryable") == False)

    # ── 9. Missing bindings and model_output returns 400 ────────────────────
    empty_request = {"constraint_set": {"objective_id": "TEST", "constraints": []}}

    response = client.post(
        '/enforce',
        data=json.dumps(empty_request),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Missing bindings/model_output returns 400",
        response.status_code == 400)
    chk("Missing bindings error type is correct",
        response.json.get("error_type") == "MISSING_BINDINGS")

    # ── 10. Malformed JSON returns 400 ──────────────────────────────────────
    response = client.post(
        '/enforce',
        data='{invalid json}',
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Malformed JSON returns 400",
        response.status_code == 400)
    chk("Malformed JSON error type is correct",
        response.json.get("error_type") == "MALFORMED_JSON")

    # ── 11. POST to non-existent endpoint returns 404 ───────────────────────
    response = client.post(
        '/nonexistent',
        data=json.dumps({}),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Non-existent endpoint returns 404",
        response.status_code == 404)
    chk("404 error type is correct",
        response.json.get("error_type") == "NOT_FOUND")

    # ── 12. GET to POST-only endpoint returns 405 ───────────────────────────
    response = client.get(
        '/enforce',
        headers={'X-API-Key': api_key},
    )

    chk("GET /enforce returns 405",
        response.status_code == 405)
    chk("405 error type is correct",
        response.json.get("error_type") == "METHOD_NOT_ALLOWED")

    # ── 13. ALLOW decision ──────────────────────────────────────────────────
    allow_request = {
        "bindings": {"age": 35, "risk": 8},
        "constraint_set": {
            "objective_id": "TEST_ALLOW",
            "constraints": ["age >= 18", "risk <= 25"],
        },
    }

    response = client.post(
        '/enforce',
        data=json.dumps(allow_request),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Valid bindings produce ALLOW decision",
        response.json.get("status") == "ALLOW")
    chk("ALLOW decision has empty violations list",
        response.json.get("violations", []) == [])

    # ── 14. BLOCK decision ──────────────────────────────────────────────────
    block_request = {
        "bindings": {"age": 16, "risk": 8},
        "constraint_set": {
            "objective_id": "TEST_BLOCK",
            "constraints": ["age >= 18", "risk <= 25"],
        },
    }

    response = client.post(
        '/enforce',
        data=json.dumps(block_request),
        content_type='application/json',
        headers={'X-API-Key': api_key},
    )

    chk("Invalid bindings produce BLOCK decision",
        response.json.get("status") == "BLOCK")
    chk("BLOCK decision has violations list",
        len(response.json.get("violations", [])) > 0)

    total = passed + failed
    print(f"\n=== Results: {passed}/{total} passed ===")
    if failed > 0:
        print("FAIL — do not commit")
        return False
    else:
        print("ALL TESTS PASSED — ready for PR")
        return True


if __name__ == "__main__":
    success = test_api_endpoints()
    sys.exit(0 if success else 1)
