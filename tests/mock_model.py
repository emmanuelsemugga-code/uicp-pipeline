#!/usr/bin/env python3
"""
mock_model.py – Stand‑alone mock model for UICP integration testing.
Replaces the live Groq API call with deterministic, pre‑defined responses.
Use with the --mock flag in demo_live_enforcement.py or import directly.

Test cases:
  0. ALLOW              (age=35, risk=8)
  1. BLOCK (age)        (age=16, risk=10)
  2. BLOCK (risk)       (age=42, risk=27)
  3. BLOCK (both)       (age=15, risk=29)
  4. INCOMPLETE (age missing) (risk=5 only)
"""

import sys

# ---------------------------------------------------------------------------
# 1. MOCK RESPONSES – exact strings returned by the mock model
# ---------------------------------------------------------------------------
MOCK_RESPONSES = [
    # 0 – compliant
    "Loan recommendation for client age 35. Assessed risk score 8. APPROVE.",
    # 1 – violates age constraint
    "Loan recommendation for client age 16. Assessed risk score 10. APPROVE.",
    # 2 – violates risk constraint
    "Loan recommendation for client age 42. Assessed risk score 27. APPROVE.",
    # 3 – violates both constraints
    "Loan recommendation for client age 15. Assessed risk score 29. APPROVE.",
    # 4 – missing variable (age not present)
    "Loan recommendation. Assessed risk score 5. APPROVE.",
]

# ---------------------------------------------------------------------------
# 2. STRUCTURED TEST CASES – what the pipeline MUST produce
# ---------------------------------------------------------------------------
MOCK_TEST_CASES = [
    {"index": 0, "description": "ALLOW",                    "expected_bindings": {"age": 35, "risk": 8},  "expected_status": "ALLOW"},
    {"index": 1, "description": "BLOCK (age violation)",     "expected_bindings": {"age": 16, "risk": 10}, "expected_status": "BLOCK"},
    {"index": 2, "description": "BLOCK (risk violation)",    "expected_bindings": {"age": 42, "risk": 27}, "expected_status": "BLOCK"},
    {"index": 3, "description": "BLOCK (both violations)",   "expected_bindings": {"age": 15, "risk": 29}, "expected_status": "BLOCK"},
    {"index": 4, "description": "BLOCK (missing age)",       "expected_bindings": {"risk": 5},              "expected_status": "BLOCK"},
]

# ---------------------------------------------------------------------------
# 3. MOCK MODEL FUNCTION – cycles through responses deterministically
# ---------------------------------------------------------------------------
_mock_index = 0

def mock_model_call(prompt: str) -> str:
    """
    Return the next pre‑defined mock response, cycling forever.
    Ignores the prompt – always returns one of the five test strings.
    """
    global _mock_index
    response = MOCK_RESPONSES[_mock_index % len(MOCK_RESPONSES)]
    _mock_index += 1
    return response

def reset_mock():
    """Reset the mock to the first response. Call before each test suite."""
    global _mock_index
    _mock_index = 0


# ---------------------------------------------------------------------------
# 4. COMMAND‑LINE INTERFACE
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # If run directly, print the five responses in order for visual check.
    print("=== Mock Model API — Dry Run ===\n")
    reset_mock()
    for i in range(5):
        resp = mock_model_call("(any prompt)")
        print(f"Response {i}: {resp}")
    print("\n=== Mock responses ready for integration tests. ===")