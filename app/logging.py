#!/usr/bin/env python3
"""
app/logging.py — GAP-22 Structured Logging

Every API request is logged to stdout as JSON lines.
Format: timestamp, masked_api_key, request_id, endpoint, status, latency_ms

No request bodies are logged (privacy).
No response bodies are logged (size).
Only metadata that matters for operations.
"""

import json
import time
from datetime import datetime, timezone
from flask import request, g


def log_request_start(request_id: str):
    """
    Called at the start of request handling.
    Stores start time and request_id in Flask g (request context).
    """
    g.request_id = request_id
    g.start_time = time.time()


def log_request_end(endpoint: str, status_code: int, error_type: str = None):
    """
    Called at the end of request handling.
    Logs the full request lifecycle to stdout.
    """
    if not hasattr(g, 'start_time'):
        return

    latency_ms = (time.time() - g.start_time) * 1000
    timestamp = datetime.now(timezone.utc).isoformat()

    # Mask API key for logging
    api_key = request.headers.get("X-API-Key", "none")
    from app.auth import mask_api_key
    masked_key = mask_api_key(api_key) if api_key != "none" else "none"

    log_entry = {
        "timestamp": timestamp,
        "request_id": g.request_id,
        "endpoint": endpoint,
        "method": request.method,
        "api_key": masked_key,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "error_type": error_type,
    }

    print(json.dumps(log_entry))


def extract_error_type(response_json: dict) -> str:
    """Extract error_type from error response for logging."""
    return response_json.get("error_type", "UNKNOWN") if response_json.get("error") else None
