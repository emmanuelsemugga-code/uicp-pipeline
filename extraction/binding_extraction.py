#!/usr/bin/env python3
"""
binding_extraction.py — Deterministic Binding‑Extraction Layer (v1.1)
Converts raw model text output into numeric bindings for the Phase 4
enforcement gateway.  No floats, no randomness, no model calls.
"""
import json
import re

INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1


def extract_bindings(model_output: str, binding_schema: dict) -> dict:
    """
    Convert a raw model output string into a set of numeric bindings.
    … (unchanged docstring)
    """
    bindings = {}
    missing = []

    for var_name, rule in binding_schema.items():
        method = rule.get("method")
        value = None

        if method == "constant":
            value = _extract_constant(rule)
        elif method == "regex":
            value = _extract_regex(model_output, rule, var_name)
        elif method == "jsonpath":
            value = _extract_jsonpath(model_output, rule, var_name)
        elif method == "tag":
            value = _extract_tag(model_output, rule, var_name)
        else:
            missing.append(var_name)
            continue

        if value is None:
            missing.append(var_name)
        else:
            bindings[var_name] = value

    if missing:
        return {
            "status": "INCOMPLETE",
            "bindings": bindings,
            "missing": missing,
        }
    return {
        "status": "COMPLETE",
        "bindings": bindings,
    }


# ---------------------------------------------------------------------------
# Extraction methods (unchanged)
# ---------------------------------------------------------------------------

def _extract_constant(rule: dict):
    """Return the constant value from a rule. Validate 128‑bit signed range."""
    val = rule.get("value")
    if isinstance(val, bool):
        return None
    if not isinstance(val, int):
        return None
    if not (INT128_MIN <= val <= INT128_MAX):
        return None
    return val


def _extract_regex(model_output: str, rule: dict, var_name: str):
    """Apply a regex with a named group 'value' and parse the capture as int."""
    pattern = rule.get("pattern")
    if not pattern or not isinstance(pattern, str):
        return None
    try:
        compiled = re.compile(pattern)
    except re.error:
        return None
    match = compiled.search(model_output)
    if not match:
        return None
    try:
        captured = match.group("value")
    except IndexError:
        return None
    if captured is None:
        return None
    return _parse_int(captured)


def _extract_jsonpath(model_output: str, rule: dict, var_name: str):
    """
    Extract a value from a JSON structure inside the model output.
    If the entire model output is not valid JSON, attempt to find the
    first JSON object (delimited by '{' and '}') and parse that.
    """
    path = rule.get("path")
    if not path or not isinstance(path, str):
        return None

    obj = None
    try:
        obj = json.loads(model_output)
    except (json.JSONDecodeError, TypeError):
        start = model_output.find("{")
        end = model_output.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(model_output[start:end+1])
            except (json.JSONDecodeError, TypeError):
                pass

    if obj is None:
        return None

    keys = path.split(".")
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return _parse_int(current)


def _extract_tag(model_output: str, rule: dict, var_name: str):
    """Extract value between [VAR:name] and [/VAR] delimiters."""
    tag_name = rule.get("tag")
    if not tag_name or not isinstance(tag_name, str):
        return None
    opening = f"[VAR:{tag_name}]"
    closing = f"[/VAR]"
    start_idx = model_output.find(opening)
    if start_idx == -1:
        return None
    start_idx += len(opening)
    end_idx = model_output.find(closing, start_idx)
    if end_idx == -1:
        return None
    captured = model_output[start_idx:end_idx].strip()
    return _parse_int(captured)


def _parse_int(value):
    """Parse a value to an integer within the 128‑bit signed range."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if INT128_MIN <= value <= INT128_MAX:
            return value
        return None
    if isinstance(value, str):
        stripped = value.strip()
        try:
            val = int(stripped)
        except ValueError:
            return None
        if INT128_MIN <= val <= INT128_MAX:
            return val
    return None
    # ═══════════════════════════════════════════════════════════════════════════════
# GAP-47 PATCH: Governed Extraction Schema
# Provides schema signing, verification, versioning, and commitment recording.
# An unsigned or tampered schema is rejected before the gateway initializes.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
from datetime import datetime, timezone

# _sign and _verify are expected to be already defined (from phase5_engine).
# If they are not present, define safe local copies for testing.
try:
    _sign
except NameError:
    def _sign(priv, data: bytes) -> str:
        return priv.sign(data).hex()

try:
    _verify
except NameError:
    def _verify(pub, sig_hex: str, data: bytes) -> bool:
        from cryptography.exceptions import InvalidSignature
        try:
            pub.verify(bytes.fromhex(sig_hex), data)
            return True
        except (InvalidSignature, ValueError):
            return False


class GovernedSchema:
    """
    GAP-47: A signed, versioned, committed extraction schema.

    The schema dict is signed with the operator's Ed25519 private key
    at registration time. The signature is verified before any extraction
    is performed. A schema modification without re-signing is detected
    and rejected.

    Every enforcement decision must record this schema's commitment_id
    so auditors can reconstruct exactly which schema governed any decision.
    """

    def __init__(self, schema: dict, name: str, version: str):
        if not isinstance(schema, dict) or len(schema) == 0:
            raise ValueError("schema must be a non-empty dict")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be a non-empty string")

        # Deep copy so that mutating the original dict doesn't corrupt this instance
        self.schema    = json.loads(json.dumps(schema))
        self.name      = name
        self.version   = version
        self.timestamp = datetime.now(timezone.utc).isoformat()

        # Computed from schema content — deterministic
        self.commitment_id = self._compute_commitment_id()

        # Set after register() is called
        self.signature: str | None = None
        self._is_registered        = False

    # ── Commitment ID ─────────────────────────────────────────────
    def _compute_commitment_id(self) -> str:
        payload = json.dumps(
            {
                "name":    self.name,
                "version": self.version,
                "schema":  self.schema,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    # ── Signing payload ───────────────────────────────────────────
    def _signing_payload(self) -> bytes:
        return json.dumps(
            {
                "commitment_id": self.commitment_id,
                "name":          self.name,
                "timestamp":     self.timestamp,
                "version":       self.version,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    # ── Registration ──────────────────────────────────────────────
    def register(self, operator_private_key) -> "GovernedSchema":
        self.signature      = _sign(operator_private_key,
                                    self._signing_payload())
        self._is_registered = True
        return self

    # ── Verification ──────────────────────────────────────────────
    def verify(self, operator_public_key) -> tuple:
        try:
            if not self._is_registered or self.signature is None:
                return False, "schema has not been registered — no signature present"

            recomputed = self._compute_commitment_id()
            if recomputed != self.commitment_id:
                return False, (
                    f"schema content has been tampered — "
                    f"commitment_id mismatch: "
                    f"stored={self.commitment_id[:16]}… "
                    f"computed={recomputed[:16]}…"
                )

            valid = _verify(
                operator_public_key,
                self.signature,
                self._signing_payload(),
            )

            if valid:
                return True, None
            return False, "signature verification failed — schema may be tampered"

        except Exception as exc:
            return False, f"verification error: {type(exc).__name__}: {exc}"

    # ── Safe extraction ───────────────────────────────────────────
    def extract(self, model_output: str, operator_public_key) -> dict:
        valid, reason = self.verify(operator_public_key)
        if not valid:
            raise RuntimeError(
                f"GAP-47: Schema integrity check failed — extraction blocked. "
                f"Reason: {reason}"
            )
        result = extract_bindings(model_output, self.schema)
        # Unwrap the status dict and return only the bindings mapping
        return result.get("bindings", {})

    # ── Serialization ─────────────────────────────────────────────
    def to_record(self) -> dict:
        return {
            "commitment_id": self.commitment_id,
            "name":          self.name,
            "version":       self.version,
            "timestamp":     self.timestamp,
            "signature":     self.signature,
            "schema":        self.schema,
        }


# ── GAP-47 Self‑Verification Suite ─────────────────────────────────
def _run_gap47_tests():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    passed = failed = 0

    def chk(label, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  GAP-47 | {label}")
        else:
            failed += 1
            print(f"  FAIL  GAP-47 | {label}" +
                  (f" — {detail}" if detail else ""))

    print("\n=== GAP-47 Governed Schema Tests ===\n")

    op_priv  = Ed25519PrivateKey.generate()
    op_pub   = op_priv.public_key()
    bad_priv = Ed25519PrivateKey.generate()
    bad_pub  = bad_priv.public_key()

    schema_dict = {
        "age":  {"method": "regex",
                 "pattern": r"(?:age|client age)[=: ]*(?P<value>\d+)"},
        "risk": {"method": "regex",
                 "pattern": r"(?i)(?:risk score|risk)[=: ]*(?P<value>\d+)"},
    }

    # 1. Construction
    gs = GovernedSchema(schema_dict, "loan_v1", "1.0.0")
    chk("GovernedSchema constructs without error", gs is not None)
    chk("commitment_id is non-empty string",
        isinstance(gs.commitment_id, str) and len(gs.commitment_id) == 64)
    chk("signature is None before register()", gs.signature is None)
    chk("is_registered is False before register()", not gs._is_registered)

    # 2. Unregistered schema rejection
    valid, reason = gs.verify(op_pub)
    chk("Unregistered schema fails verification", not valid, reason)
    chk("Unregistered schema failure reason is meaningful",
        reason is not None and len(reason) > 0)
    try:
        gs.extract("client age: 35, risk score: 8", op_pub)
        chk("Unregistered schema blocks extraction", False,
            "no RuntimeError raised")
    except RuntimeError:
        chk("Unregistered schema blocks extraction", True)

    # 3. Registration and verification
    gs.register(op_priv)
    chk("After register() signature is non-empty string",
        isinstance(gs.signature, str) and len(gs.signature) > 0)
    chk("After register() is_registered is True", gs._is_registered)
    valid2, reason2 = gs.verify(op_pub)
    chk("Registered schema passes verification with correct key",
        valid2, reason2)

    # 4. Wrong key rejected
    valid_w, reason_w = gs.verify(bad_pub)
    chk("Schema signed by op_key rejected by bad_pub",
        not valid_w, reason_w)

    # 5. Tampered schema detection
    gs_tampered = GovernedSchema(schema_dict, "loan_v1", "1.0.0")
    gs_tampered.register(op_priv)
    gs_tampered.schema["age"]["pattern"] = r"(?P<value>\d+)"
    valid_t, reason_t = gs_tampered.verify(op_pub)
    chk("Tampered schema content detected by verify()",
        not valid_t, reason_t)
    try:
        gs_tampered.extract("client age: 35", op_pub)
        chk("Tampered schema blocks extraction", False,
            "no RuntimeError raised")
    except RuntimeError:
        chk("Tampered schema blocks extraction", True)

    # 6. Valid extraction
    output = "Loan for client age: 35. Risk score: 8. APPROVE."
    bindings = gs.extract(output, op_pub)
    chk("Valid schema extracts age correctly",
        bindings.get("age") == 35, f"got {bindings.get('age')}")
    chk("Valid schema extracts risk correctly",
        bindings.get("risk") == 8, f"got {bindings.get('risk')}")

    # 7. Deterministic commitment ID
    gs2 = GovernedSchema(schema_dict, "loan_v1", "1.0.0")
    chk("Same schema content produces same commitment_id",
        gs.commitment_id == gs2.commitment_id)
    gs3 = GovernedSchema(
        {"age": {"method": "regex", "pattern": r"(?P<value>\d+)"}},
        "loan_v1", "1.0.0"
    )
    chk("Different schema content produces different commitment_id",
        gs.commitment_id != gs3.commitment_id)

    # 8. Serialization
    record = gs.to_record()
    required_keys = {"commitment_id", "name", "version",
                     "timestamp", "signature", "schema"}
    chk("to_record() contains all required keys",
        required_keys.issubset(record.keys()))
    chk("to_record() commitment_id matches schema",
        record["commitment_id"] == gs.commitment_id)

    # 9. Invalid construction
    try:
        GovernedSchema({}, "test", "1.0.0")
        chk("Empty schema dict raises ValueError", False)
    except ValueError:
        chk("Empty schema dict raises ValueError", True)
    try:
        GovernedSchema(schema_dict, "", "1.0.0")
        chk("Empty name raises ValueError", False)
    except ValueError:
        chk("Empty name raises ValueError", True)

    total = passed + failed
    print(f"\n=== GAP-47 Results: {passed}/{total} passed ===")
    if failed > 0:
        print("FAIL — do not commit")
    else:
        print("ALL GAP-47 TESTS PASSED — ready for PR")

    return passed, failed
    # ---------------------------------------------------------------------------
# Built‑in test harness (17 original checks + GAP‑47 suite)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    PASS = FAIL = 0

    def check(label, condition, detail=""):
        global PASS, FAIL
        if condition:
            PASS += 1
            print(f"  ✓  {label}")
        else:
            FAIL += 1
            print(f"  ✗  {label}  —  {detail}")

    print("=== Binding‑Extraction Layer Test Suite (v1.1) ===\n")

    # 1. Valid regex extraction (case‑insensitive)
    print("1. Valid regex extraction")
    schema = {"risk": {"method": "regex", "pattern": r"(?i)single[ -]position risk[ =:]+(?P<value>-?\d+)"}}
    output = "Portfolio analysis complete. Single-position risk = 27. Recommended."
    result = extract_bindings(output, schema)
    check("status COMPLETE", result["status"] == "COMPLETE")
    check("risk = 27", result["bindings"].get("risk") == 27)

    # 2. Non‑matching regex
    print("\n2. Non‑matching regex")
    output2 = "No risk data available."
    result2 = extract_bindings(output2, schema)
    check("status INCOMPLETE", result2["status"] == "INCOMPLETE")
    check("risk in missing", "risk" in result2.get("missing", []))

    # 3. Valid JSONPath extraction
    print("\n3. Valid JSONPath extraction")
    schema3 = {"age": {"method": "jsonpath", "path": "client.age"}}
    output3 = '{"client": {"name": "Alice", "age": 42}}'
    result3 = extract_bindings(output3, schema3)
    check("status COMPLETE", result3["status"] == "COMPLETE")
    check("age = 42", result3["bindings"].get("age") == 42)

    # 4. Invalid JSONPath
    print("\n4. Invalid JSONPath (wrong path)")
    output4 = '{"client": {"name": "Bob"}}'
    result4 = extract_bindings(output4, schema3)
    check("status INCOMPLETE", result4["status"] == "INCOMPLETE")

    # 5. Valid tag extraction
    print("\n5. Valid tag extraction")
    schema5 = {"loan": {"method": "tag", "tag": "LOAN_AMOUNT"}}
    output5 = "Recommendation: approve loan of [VAR:LOAN_AMOUNT]15000[/VAR] to customer."
    result5 = extract_bindings(output5, schema5)
    check("status COMPLETE", result5["status"] == "COMPLETE")
    check("loan = 15000", result5["bindings"].get("loan") == 15000)

    # 6. Constant extraction
    print("\n6. Constant extraction (independent of model output)")
    schema6 = {"max_exposure": {"method": "constant", "value": 1_000_000}}
    result6 = extract_bindings("any output", schema6)
    check("status COMPLETE", result6["status"] == "COMPLETE")
    check("max_exposure = 1,000,000", result6["bindings"].get("max_exposure") == 1_000_000)

    # 7. Mixed schema (regex + constant + JSONPath) — JSON object embedded in text
    print("\n7. Mixed schema (regex + constant + JSONPath)")
    schema7 = {
        "risk": {"method": "regex", "pattern": r"risk[ =:]+(?P<value>-?\d+)"},
        "max_exposure": {"method": "constant", "value": 500_000},
        "age": {"method": "jsonpath", "path": "client.age"},
    }
    output7 = '{"client": {"age": 35}}  risk = 12  '
    result7 = extract_bindings(output7, schema7)
    check("status COMPLETE", result7["status"] == "COMPLETE")
    check("risk = 12", result7["bindings"].get("risk") == 12)
    check("max_exposure = 500,000", result7["bindings"].get("max_exposure") == 500_000)
    check("age = 35", result7["bindings"].get("age") == 35)

    # 8. Empty model output
    print("\n8. Empty model output")
    schema8 = {"risk": {"method": "regex", "pattern": r"risk[ =:]+(?P<value>-?\d+)"}}
    result8 = extract_bindings("", schema8)
    check("status INCOMPLETE", result8["status"] == "INCOMPLETE")
    check("risk in missing", "risk" in result8.get("missing", []))

    total_original = PASS + FAIL
    print(f"\n=== Original Results: {PASS}/{total_original} passed ===")

    # ── Run GAP‑47 suite ───────────────────────────────────────────
    gap47_passed, gap47_failed = _run_gap47_tests()

    # ── Combined totals ────────────────────────────────────────────
    combined_pass = PASS + gap47_passed
    combined_fail = FAIL + gap47_failed
    print("\n" + "="*60)
    print(f"COMBINED RESULTS: {combined_pass} passed, {combined_fail} failed")
    if combined_fail == 0:
        print("  ✓ ALL TESTS PASS — Extraction layer with GAP‑47 is ALIGNED.\n")
    else:
        print(f"  ✗ {combined_fail} FAILURE(S) — Extraction layer is NOT aligned.\n")
