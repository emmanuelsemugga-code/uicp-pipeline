#!/usr/bin/env python3
"""
app/auth.py — GAP-22 API Authentication

Simple API key authentication via X-API-Key header.
All routes protected by @require_api_key decorator.
Key is environment variable API_KEY at startup.
"""

import os
from functools import wraps
from flask import request, jsonify


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


def get_api_key_from_env() -> str:
    """
    Load API key from environment variable at startup.
    Fail immediately if not set — do not allow unauthenticated gateway.
    """
    key = os.environ.get("API_KEY")
    if not key:
        raise ValueError(
            "FATAL: API_KEY environment variable not set. "
            "The gateway requires authentication. "
            "Set API_KEY before starting."
        )
    if len(key) < 8:
        raise ValueError(
            "FATAL: API_KEY must be at least 8 characters. "
            "Example: export API_KEY='sk-test-abc123def456'"
        )
    return key


def verify_api_key(provided_key: str, expected_key: str) -> bool:
    """
    Constant-time comparison to prevent timing attacks.
    """
    import hmac
    return hmac.compare_digest(provided_key, expected_key)


def require_api_key(f):
    """
    Decorator for Flask routes requiring API authentication.
    Checks X-API-Key header. Rejects if missing or wrong.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key_from_env = os.environ.get("API_KEY")
        provided_key = request.headers.get("X-API-Key")

        if not provided_key:
            return jsonify({
                "error": True,
                "error_type": "MISSING_API_KEY",
                "message": "X-API-Key header is required",
                "retryable": False,
                "request_id": kwargs.get("request_id", "unknown"),
            }), 401

        if not verify_api_key(provided_key, api_key_from_env):
            return jsonify({
                "error": True,
                "error_type": "INVALID_API_KEY",
                "message": "X-API-Key is invalid",
                "retryable": False,
                "request_id": kwargs.get("request_id", "unknown"),
            }), 401

        return f(*args, **kwargs)

    return decorated_function


def mask_api_key(key: str, visible_chars: int = 8) -> str:
    """
    Mask API key for logging — show only first N chars.
    Example: sk-test-abc123def456 → sk-test-...
    """
    if len(key) <= visible_chars:
        return "***"
    return key[:visible_chars] + "..."
