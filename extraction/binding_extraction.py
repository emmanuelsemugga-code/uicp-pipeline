     #!/usr/bin/env python3
"""
binding_extraction.py — Deterministic Binding‑Extraction Layer (GAP‑36 enriched)
"""
import json, re, hashlib

INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1


def extract_bindings(model_output: str, binding_schema: dict) -> dict:
    """
    GAP-36 PATCH: Enriched binding extraction.

    Returns binding values WITH forensic evidence per binding:
    - format_hash: full SHA-256 of the exact matched substring
    - extraction_method: which method produced this value
    - matched_substring: the exact text fragment matched
    """
    bindings         = {}
    binding_evidence = {}
    missing          = []

    for var_name, config in binding_schema.items():
        method = config.get("method")
        result = None
        matched_substring = None

        # ── Extraction ────────────────────────────────────────────
        if method == "regex":
            pattern = config.get("pattern", "")
            match   = re.search(pattern, model_output, re.IGNORECASE)
            if match:
                raw = match.group("value")
                result = _parse_int(raw)
                if result is not None:
                    matched_substring = match.group(0)

        elif method == "jsonpath":
            path  = config.get("path", "")
            value = _extract_jsonpath(model_output, path)
            if value is not None:
                result = _parse_int(str(value))
                if result is not None:
                    matched_substring = str(value)

        elif method == "tag":
            tag_name = config.get("tag", var_name)
            tag_pattern = rf"\[{tag_name}:(?P<value>[^\]]+)\]"
            match = re.search(tag_pattern, model_output, re.IGNORECASE)
            if match:
                raw = match.group("value").strip()
                result = _parse_int(raw)
                if result is not None:
                    matched_substring = match.group(0)

        elif method == "constant":
            result = _parse_int(str(config.get("value", "")))
            matched_substring = str(config.get("value", ""))

        # ── Forensic evidence ─────────────────────────────────────
        if result is not None and matched_substring is not None:
            format_hash = hashlib.sha256(
                matched_substring.encode('utf-8')
            ).hexdigest()

            bindings[var_name] = result
            binding_evidence[var_name] = {
                "value":              result,
                "format_hash":        format_hash,
                "extraction_method":  method,
                "matched_substring":  matched_substring,
            }
        else:
            missing.append(var_name)

    # ── GAP-36: Multi-value consistency check ─────────────────────
    injection_warnings = _check_multi_match_consistency(
        model_output, binding_schema, bindings
    )

    if missing:
        return {
            "status":             "INCOMPLETE",
            "bindings":           bindings,
            "binding_evidence":   binding_evidence,
            "missing":            missing,
            "injection_warnings": injection_warnings,
        }

    return {
        "status":             "COMPLETE",
        "bindings":           bindings,
        "binding_evidence":   binding_evidence,
        "injection_warnings": injection_warnings,
    }


def _check_multi_match_consistency(
        model_output: str,
        binding_schema: dict,
        extracted_bindings: dict) -> list:
    """
    GAP-36: Detect multiple different values matching the same
    extraction pattern in the output — a key signal of prompt injection.
    """
    warnings = []

    for var_name, config in binding_schema.items():
        if config.get("method") != "regex":
            continue

        pattern = config.get("pattern", "")
        try:
            all_matches = list(re.finditer(pattern, model_output, re.IGNORECASE))
        except re.error:
            continue

        if len(all_matches) <= 1:
            continue

        values = []
        for m in all_matches:
            raw = m.group("value")
            parsed = _parse_int(raw)
            if parsed is not None:
                values.append({
                    "value":      parsed,
                    "substring":  m.group(0),
                    "format_hash": hashlib.sha256(
                        m.group(0).encode('utf-8')
                    ).hexdigest()
                })

        unique_values = set(v["value"] for v in values)
        if len(unique_values) > 1:
            warnings.append({
                "variable":        var_name,
                "warning_type":    "MULTI_VALUE_INCONSISTENCY",
                "severity":        "HIGH — potential prompt injection",
                "values_found":    values,
                "value_used":      extracted_bindings.get(var_name),
                "recommendation":  "BLOCK or escalate for human review",
            })

    return warnings


# ── Original helper functions (unchanged) ──────────────────────────
def _extract_constant(rule: dict):
    val = rule.get("value")
    if isinstance(val, bool): return None
    if not isinstance(val, int): return None
    if not (INT128_MIN <= val <= INT128_MAX): return None
    return val

def _extract_jsonpath(model_output: str, path: str):
    if not path: return None
    obj = None
    try:
        obj = json.loads(model_output)
    except (json.JSONDecodeError, TypeError):
        start = model_output.find("{")
        end   = model_output.rfind("}")
        if start != -1 and end != -1 and end > start:
            try: obj = json.loads(model_output[start:end+1])
            except (json.JSONDecodeError, TypeError): pass
    if obj is None: return None
    keys = path.split(".")
    cur  = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur: cur = cur[k]
        else: return None
    return cur

def _parse_int(value):
    if isinstance(value, bool): return None
    if isinstance(value, int):
        return value if INT128_MIN <= value <= INT128_MAX else None
    if isinstance(value, str):
        stripped = value.strip()
        try: val = int(stripped)
        except ValueError: return None
        return val if INT128_MIN <= val <= INT128_MAX else None
    return None 
class TrustedSourceRegistry:
    """
    GAP-36: Optional trusted source verification for binding values.

    Operators register authoritative data sources for specific variables.
    Before enforcement, extracted binding values are compared against
    the authoritative values. A mismatch produces BINDING_MISMATCH.

    Where no trusted source is registered, the system proceeds with
    extraction but documents the unverified status in the audit record.
    """

    def __init__(self):
        self._sources: dict = {}

    def register(self, var_name: str, source_fn) -> "TrustedSourceRegistry":
        if not callable(source_fn):
            raise ValueError(f"source_fn for '{var_name}' must be callable")
        self._sources[var_name] = source_fn
        return self

    def verify(self, output_id: str, extracted_bindings: dict,
               binding_evidence: dict) -> dict:
        verified      = []
        unverified    = []
        mismatches    = []
        source_errors = []

        for var_name, extracted_value in extracted_bindings.items():
            if var_name not in self._sources:
                unverified.append(var_name)
                continue

            try:
                authoritative = self._sources[var_name](output_id)
                if authoritative is None:
                    source_errors.append({
                        "variable": var_name,
                        "error": "trusted source returned None — unavailable",
                    })
                    unverified.append(var_name)
                    continue

                authoritative = int(authoritative)
                if authoritative == extracted_value:
                    verified.append(var_name)
                else:
                    mismatches.append({
                        "variable":            var_name,
                        "extracted_value":     extracted_value,
                        "authoritative_value": authoritative,
                        "format_hash": binding_evidence.get(
                            var_name, {}).get("format_hash", "UNKNOWN"),
                        "verdict":  "BINDING_MISMATCH",
                        "severity": "CRITICAL — potential injection",
                    })
            except Exception as exc:
                source_errors.append({
                    "variable": var_name,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                unverified.append(var_name)

        return {
            "verified":      verified,
            "unverified":    unverified,
            "mismatches":    mismatches,
            "source_errors": source_errors,
        }

    def has_mismatches(self, verification_record: dict) -> bool:
        return len(verification_record.get("mismatches", [])) > 0
