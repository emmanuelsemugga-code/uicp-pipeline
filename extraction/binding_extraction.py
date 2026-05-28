#!/usr/bin/env python3
"""
binding_extraction.py — Deterministic Binding‑Extraction Layer
(GAP‑36 + GAP‑43 enriched, GAP‑47 governed schema)
"""
import json, re, hashlib, os, tempfile
from datetime import datetime, timezone

# PersonalDataStore is already in memory from the GAP‑44 cell.
# No file import needed.

INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1

# ═══════════════════ Original helpers ═══════════════════
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

# ═══════════════════ GAP‑36 + GAP‑43 extraction ═══════════════════
def extract_bindings(model_output: str,
                     binding_schema: dict,
                     personal_data_store=None) -> dict:
    bindings         = {}
    binding_evidence = {}
    missing          = []

    for var_name, config in binding_schema.items():
        method = config.get("method")
        result = None
        matched_substring = None

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
            opening = f"[VAR:{tag_name}]"
            closing = "[/VAR]"
            start_idx = model_output.find(opening)
            if start_idx != -1:
                start_idx += len(opening)
                end_idx = model_output.find(closing, start_idx)
                if end_idx != -1:
                    raw = model_output[start_idx:end_idx].strip()
                    result = _parse_int(raw)
                    if result is not None:
                        matched_substring = f"[VAR:{tag_name}]{raw}[/VAR]"

        elif method == "constant":
            result = _parse_int(str(config.get("value", "")))
            matched_substring = str(config.get("value", ""))

        if result is not None and matched_substring is not None:
            format_hash = hashlib.sha256(
                matched_substring.encode('utf-8')
            ).hexdigest()
            bindings[var_name] = result

            if personal_data_store is not None:
                value_record_id = personal_data_store.write(
                    decision_id   = f"extraction:{id(model_output)}",
                    variable_name = f"{var_name}:value",
                    actual_value  = result,
                )
                substr_hash = hashlib.sha256(
                    matched_substring.encode('utf-8')
                ).hexdigest()
                binding_evidence[var_name] = {
                    "value_hash":              PersonalDataStore.compute_hash(result),
                    "matched_substring_hash":  substr_hash,
                    "format_hash":             format_hash,
                    "extraction_method":       method,
                    "personal_data_record_id": value_record_id,
                    "value_protected":         True,
                }
            else:
                binding_evidence[var_name] = {
                    "value":              result,
                    "value_hash":         PersonalDataStore.compute_hash(result),
                    "matched_substring":  matched_substring,
                    "format_hash":        format_hash,
                    "extraction_method":  method,
                    "value_protected":    False,
                }
        else:
            missing.append(var_name)

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

def _check_multi_match_consistency(model_output, binding_schema, extracted_bindings):
    warnings = []
    for var_name, config in binding_schema.items():
        if config.get("method") != "regex": continue
        pattern = config.get("pattern", "")
        try:
            all_matches = list(re.finditer(pattern, model_output, re.IGNORECASE))
        except re.error: continue
        if len(all_matches) <= 1: continue
        values = []
        for m in all_matches:
            raw = m.group("value")
            parsed = _parse_int(raw)
            if parsed is not None:
                values.append({
                    "value": parsed, "substring": m.group(0),
                    "format_hash": hashlib.sha256(m.group(0).encode()).hexdigest()
                })
        unique_values = set(v["value"] for v in values)
        if len(unique_values) > 1:
            warnings.append({
                "variable": var_name, "warning_type": "MULTI_VALUE_INCONSISTENCY",
                "severity": "HIGH — potential prompt injection",
                "values_found": values,
                "value_used": extracted_bindings.get(var_name),
                "recommendation": "BLOCK or escalate for human review",
            })
    return warnings

# ═══════════════════ GAP‑36 TrustedSourceRegistry ═══════════════════
class TrustedSourceRegistry:
    def __init__(self): self._sources = {}
    def register(self, var_name, source_fn):
        if not callable(source_fn): raise ValueError("must be callable")
        self._sources[var_name] = source_fn
        return self
    def verify(self, output_id, extracted_bindings, binding_evidence):
        verified, unverified, mismatches, source_errors = [], [], [], []
        for var_name, extracted_value in extracted_bindings.items():
            if var_name not in self._sources:
                unverified.append(var_name); continue
            try:
                authoritative = self._sources[var_name](output_id)
                if authoritative is None:
                    source_errors.append({"variable":var_name,"error":"returned None"})
                    unverified.append(var_name); continue
                authoritative = int(authoritative)
                if authoritative == extracted_value:
                    verified.append(var_name)
                else:
                    mismatches.append({
                        "variable":var_name,"extracted_value":extracted_value,
                        "authoritative_value":authoritative,
                        "format_hash":binding_evidence.get(var_name,{}).get("format_hash","UNKNOWN"),
                        "verdict":"BINDING_MISMATCH","severity":"CRITICAL"
                    })
            except Exception as exc:
                source_errors.append({"variable":var_name,"error":f"{type(exc).__name__}:{exc}"})
                unverified.append(var_name)
        return {"verified":verified,"unverified":unverified,"mismatches":mismatches,"source_errors":source_errors}
    def has_mismatches(self, vr): return len(vr.get("mismatches",[])) > 0

# ═══════════════════ GAP‑47 GovernedSchema ═══════════════════
try: _sign
except NameError:
    def _sign(priv, data): return priv.sign(data).hex()
try: _verify
except NameError:
    def _verify(pub, sig_hex, data):
        from cryptography.exceptions import InvalidSignature
        try: pub.verify(bytes.fromhex(sig_hex), data); return True
        except (InvalidSignature, ValueError): return False

class GovernedSchema:
    def __init__(self, schema, name, version):
        if not isinstance(schema, dict) or len(schema)==0: raise ValueError("schema must be non‑empty")
        if not isinstance(name, str) or not name.strip(): raise ValueError("name must be non‑empty")
        if not isinstance(version, str) or not version.strip(): raise ValueError("version must be non‑empty")
        self.schema    = json.loads(json.dumps(schema))
        self.name      = name
        self.version   = version
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.commitment_id = self._compute_commitment_id()
        self.signature     = None
        self._is_registered = False
    def _compute_commitment_id(self):
        payload = json.dumps({"name":self.name,"version":self.version,"schema":self.schema}, sort_keys=True, separators=(",",":")).encode()
        return hashlib.sha256(payload).hexdigest()
    def _signing_payload(self):
        return json.dumps({"commitment_id":self.commitment_id,"name":self.name,"timestamp":self.timestamp,"version":self.version}, sort_keys=True, separators=(",",":")).encode()
    def register(self, operator_private_key):
        self.signature = _sign(operator_private_key, self._signing_payload())
        self._is_registered = True
        return self
    def verify(self, operator_public_key):
        try:
            if not self._is_registered or self.signature is None: return False, "not registered"
            recomputed = self._compute_commitment_id()
            if recomputed != self.commitment_id: return False, "schema content tampered"
            valid = _verify(operator_public_key, self.signature, self._signing_payload())
            return (True, None) if valid else (False, "signature verification failed")
        except Exception as e: return False, f"verification error: {type(e).__name__}: {e}"
    def extract(self, model_output, operator_public_key):
        valid, reason = self.verify(operator_public_key)
        if not valid: raise RuntimeError(f"GAP-47: Schema integrity check failed. Reason: {reason}")
        result = extract_bindings(model_output, self.schema)
        return result.get("bindings", {})
    def to_record(self):
        return {"commitment_id":self.commitment_id,"name":self.name,"version":self.version,"timestamp":self.timestamp,"signature":self.signature,"schema":self.schema}
