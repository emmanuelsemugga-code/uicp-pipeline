#!/usr/bin/env python3
"""
app/errors.py — GAP-22 Error Handling

All errors return a standardized JSON response.
HTTP status codes follow REST conventions.
Every error includes retryable flag so clients know whether to retry.
"""

from flask import jsonify


class APIError(Exception):
    """Base class for all API errors."""
    def __init__(self,
                 error_type: str,
                 message: str,
                 http_status: int,
                 retryable: bool = False):
        self.error_type = error_type
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        super().__init__(self.message)


# Specific error types
class MissingConstraintSet(APIError):
    def __init__(self):
        super().__init__(
            error_type="MISSING_CONSTRAINT_SET",
            message="constraint_set is required in request body",
            http_status=400,
            retryable=False,
        )


class MissingBindings(APIError):
    def __init__(self):
        super().__init__(
            error_type="MISSING_BINDINGS",
            message="bindings dict or model_output is required",
            http_status=400,
            retryable=False,
        )


class MalformedJSON(APIError):
    def __init__(self, detail: str = ""):
        super().__init__(
            error_type="MALFORMED_JSON",
            message=f"Request body is not valid JSON. {detail}",
            http_status=400,
            retryable=False,
        )


class EnforcementError(APIError):
    def __init__(self, detail: str = ""):
        super().__init__(
            error_type="ENFORCEMENT_ERROR",
            message=f"Enforcement engine error: {detail}",
            http_status=500,
            retryable=True,
        )


class EncryptionKeyUnavailable(APIError):
    def __init__(self):
        super().__init__(
            error_type="ENCRYPTION_KEY_UNAVAILABLE",
            message="Encryption key for personal data store is not available",
            http_status=500,
            retryable=True,
        )


class ConstraintSetLoadError(APIError):
    def __init__(self, detail: str = ""):
        super().__init__(
            error_type="CONSTRAINT_SET_LOAD_ERROR",
            message=f"Could not load constraint set: {detail}",
            http_status=500,
            retryable=True,
        )


class GatewayUnavailable(APIError):
    def __init__(self):
        super().__init__(
            error_type="GATEWAY_UNAVAILABLE",
            message="Enforcement gateway is unavailable",
            http_status=503,
            retryable=True,
        )


def error_response(error: APIError, request_id: str) -> tuple:
    """
    Format an APIError as a Flask JSON response.
    Returns (json_response, http_status_code).
    """
    return jsonify({
        "error": True,
        "error_type": error.error_type,
        "message": error.message,
        "retryable": error.retryable,
        "request_id": request_id,
    }), error.http_status
