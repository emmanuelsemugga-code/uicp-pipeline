#!/usr/bin/env python3
"""
Phase 4 – UICP Runtime Enforcement Gateway (monolithic, Colab‑ready)
GAP‑20 PATCH: AuditLog abstraction for multi‑instance readiness.
All original enforcement logic untouched.
"""
import hashlib, json, re, os, uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1
ENFORCEABLE_CLASSIFICATIONS = {"LINEAR_SINGLE_VAR", "LINEAR_MULTI_VAR"}
REVIEW_CLASSIFICATIONS = {"NONLINEAR", "OUT_OF_SCOPE"}

_TOKEN_RE = re.compile(
    r"\s*(?:"
    r"(?P<INT>-?\d+)"
    r"|(?P<VAR>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<OP>>=|<=|!=|>|<|=)"
    r"|(?P<PLUS>\+)"
    r"|(?P<MINUS>-)"
    r"|(?P<STAR>\*)"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r")\s*"
)

class ParseError(Exception):
    pass

class _Lexer:
    def __init__(self, text):
        self._tokens = []
        pos = 0
        while pos < len(text):
            m = _TOKEN_RE.match(text, pos)
            if not m:
                raise ParseError(f"Unexpected character at position {pos}: {text[pos]!r}")
            kind = m.lastgroup
            value = m.group()
            self._tokens.append((kind, value.strip()))
            pos = m.end()
        self._pos = 0
    def peek(self):
        if self._pos < len(self._tokens): return self._tokens[self._pos]
        return None
    def consume(self):
        tok = self._tokens[self._pos]; self._pos += 1; return tok
    def expect(self, kind):
        tok = self.peek()
        if tok is None or tok[0] != kind: raise ParseError(f"Expected {kind}, got {tok}")
        return self.consume()

class _Parser:
    def __init__(self, lexer): self._lex = lexer
    def parse_comparison(self):
        left = self._expr()
        tok = self._lex.peek()
        if tok is None or tok[0] != "OP": raise ParseError("Expected comparison operator")
        self._lex.consume(); op = tok[1]
        right = self._expr()
        if self._lex.peek() is not None: raise ParseError("Unexpected tokens after comparison")
        return left, op, right
    def _expr(self):
        node = self._term()
        while True:
            tok = self._lex.peek()
            if tok and tok[0] == "PLUS": self._lex.consume(); node = ("add", node, self._term())
            elif tok and tok[0] == "MINUS": self._lex.consume(); node = ("sub", node, self._term())
            else: break
        return node
    def _term(self):
        node = self._factor()
        while True:
            tok = self._lex.peek()
            if tok and tok[0] == "STAR": self._lex.consume(); node = ("mul", node, self._factor())
            else: break
        return node
    def _factor(self):
        tok = self._lex.peek()
        if tok is None: raise ParseError("Unexpected end of expression")
        if tok[0] == "INT": self._lex.consume(); return ("int", int(tok[1]))
        if tok[0] == "VAR": self._lex.consume(); return ("var", tok[1])
        if tok[0] == "MINUS": self._lex.consume(); return ("neg", self._factor())
        if tok[0] == "LPAREN": self._lex.consume(); node = self._expr(); self._lex.expect("RPAREN"); return node
        raise ParseError(f"Unexpected token: {tok}")

def _evaluate_node(node, bindings):
    kind = node[0]
    if kind == "int": return node[1]
    if kind == "var":
        name = node[1]
        if name not in bindings: raise KeyError(f"Variable '{name}' not in bindings")
        return bindings[name]
    if kind == "neg": return -_evaluate_node(node[1], bindings)
    if kind == "add": return _evaluate_node(node[1], bindings) + _evaluate_node(node[2], bindings)
    if kind == "sub": return _evaluate_node(node[1], bindings) - _evaluate_node(node[2], bindings)
    if kind == "mul": return _evaluate_node(node[1], bindings) * _evaluate_node(node[2], bindings)
    raise ParseError(f"Unknown AST node kind: {kind}")

def _apply_op(left, op, right):
    if op == ">=": return left >= right
    if op == "<=": return left <= right
    if op == ">": return left > right
    if op == "<": return left < right
    if op in ("=", "=="): return left == right
    if op == "!=": return left != right
    raise ParseError(f"Unknown operator: {op!r}")

def evaluate_canonical_form(canonical_form, bindings):
    lexer = _Lexer(canonical_form); parser = _Parser(lexer)
    left_node, op, right_node = parser.parse_comparison()
    left_val = _evaluate_node(left_node, bindings); right_val = _evaluate_node(right_node, bindings)
    result = _apply_op(left_val, op, right_val)
    return result, left_val

# ── GAP‑42 signing function ────────────────────────────────
if '_sign' not in dir():
    def _sign(priv, data):
        return priv.sign(data).hex()

# ── GAP‑20 AuditLog abstraction ─────────────────────────────
class AuditLog(ABC):
    @abstractmethod
    def append(self, decision: dict) -> str: ...
    @abstractmethod
    def get_by_id(self, decision_id: str) -> dict | None: ...
    @abstractmethod
    def list_recent(self, limit: int = 100) -> list[dict]: ...
    @abstractmethod
    def export_range(self, start_date: str, end_date: str) -> list[dict]: ...
    @abstractmethod
    def verify_chain(self) -> bool: ...

class LocalFileAuditLog(AuditLog):
    """Single‑instance in‑memory audit log – identical behaviour to original gateway."""
    def __init__(self):
        self._entries: list[dict] = []
    def append(self, decision: dict) -> str:
        prev_hash = self._entries[-1]["_chain_hash"] if self._entries else "GENESIS"
        chain_input = prev_hash + decision["decision_id"]
        chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        entry = {**decision, "_chain_hash": chain_hash}
        self._entries.append(entry)
        return decision["decision_id"]
    def get_by_id(self, decision_id: str) -> dict | None:
        for e in self._entries:
            if e.get("decision_id") == decision_id:
                return e
        return None
    def list_recent(self, limit: int = 100) -> list[dict]:
        return self._entries[-limit:]
    def export_range(self, start_date: str, end_date: str) -> list[dict]:
        return [e for e in self._entries if start_date <= e.get("timestamp","") <= end_date]
    def verify_chain(self) -> bool:
        running = "GENESIS"
        for e in self._entries:
            expected = hashlib.sha256((running + e["decision_id"]).encode()).hexdigest()
            if e.get("_chain_hash") != expected:
                return False
            running = e["_chain_hash"]
        return True
    def get_all(self) -> list[dict]:
        return list(self._entries)
        class Phase4EnforcementGateway:
    def __init__(self, gateway_private_key=None, audit_log=None):
        self._enforceable = []
        self._review_queue = []
        self._decision_log = []               # kept for backward compatibility
        self._loaded = False
        self._gateway_private_key = gateway_private_key
        self._commitment_id = "UNSET"
        self._audit_log = audit_log           # GAP‑20: swappable audit backend

    # ═══════════════════════════════════════════════════════════════
    # PATCHED: accepts both a Phase 3 output dict AND a plain list
    # ═══════════════════════════════════════════════════════════════
    def load_phase3_contract(self, contract):
        if self._loaded:
            raise RuntimeError("Contract already loaded.")
        if isinstance(contract, list):
            for item in contract:
                if isinstance(item, str):
                    self._enforceable.append({
                        "identity_string": item,
                        "canonical_form": item,
                        "classification": "LINEAR_SINGLE_VAR",
                        "derived_from": [item],
                        "reason": "",
                    })
                else:
                    self._enforceable.append(item)
            self._loaded = True
            return
        if not isinstance(contract, dict):
            raise RuntimeError("Contract must be a list or a dict.")
        status = contract.get("status")
        if status != "OK":
            raise RuntimeError(f"Phase 3 contract rejected: status={status!r}")
        raw = contract.get("canonical_constraints")
        if not isinstance(raw, list):
            raise RuntimeError("Missing canonical_constraints list.")
        for entry in raw:
            classification = entry.get("classification", "")
            identity_string = entry.get("identity_string")
            canonical_form = entry.get("canonical_form")
            if not identity_string or not isinstance(identity_string, str):
                raise RuntimeError("Invalid identity_string")
            if classification in ENFORCEABLE_CLASSIFICATIONS:
                if not canonical_form or not isinstance(canonical_form, str):
                    raise RuntimeError("Missing canonical_form")
                try:
                    _Parser(_Lexer(canonical_form)).parse_comparison()
                except ParseError as e:
                    raise RuntimeError(f"Unparseable canonical_form: {canonical_form!r}: {e}")
                self._enforceable.append({
                    "identity_string": identity_string,
                    "canonical_form": canonical_form,
                    "classification": classification,
                    "derived_from": entry.get("derived_from", []),
                    "reason": entry.get("reason", ""),
                })
            elif classification in REVIEW_CLASSIFICATIONS:
                self._review_queue.append({
                    "identity_string": identity_string,
                    "canonical_form": canonical_form,
                    "classification": classification,
                    "reason": entry.get("reason", ""),
                    "review_status": "PENDING_MANUAL_REVIEW",
                })
            else:
                raise RuntimeError(f"Unknown classification {classification!r}")
        self._loaded = True

    def _validate_bindings(self, bindings):
        if not isinstance(bindings, dict): raise ValueError("bindings must be a dict")
        validated = {}
        for k,v in bindings.items():
            if not isinstance(k, str): raise ValueError(f"Binding key {k!r} is not a string")
            if isinstance(v, bool): raise ValueError(f"Binding value for {k!r} is boolean, not integer")
            if not isinstance(v, int): raise ValueError(f"Binding value for {k!r} is {type(v).__name__!r}, not integer")
            if not (INT128_MIN <= v <= INT128_MAX): raise ValueError(f"Binding value for {k!r} out of 128‑bit range")
            validated[k] = v
        return validated

    def _evaluate_all(self, bindings):
        violations = []
        for c in self._enforceable:
            try:
                passed, actual_value = evaluate_canonical_form(c["canonical_form"], bindings)
            except KeyError as exc:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],
                                   "actual_value":f"MISSING_VARIABLE: {exc}","expected":c["canonical_form"]})
                continue
            except ParseError as exc:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],
                                   "actual_value":f"PARSE_ERROR: {exc}","expected":c["canonical_form"]})
                continue
            if not passed:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],
                                   "actual_value":actual_value,"expected":c["canonical_form"]})
        return violations

    # ── GAP‑21 PATCH ────────────────────────────────────────────
    def check_output(self, request):
        try:
            if not isinstance(request, dict):
                return self._unavailable_block(
                    output_id="UNKNOWN",
                    reason=f"request must be dict, got {type(request).__name__}"
                )
            output_id = request.get("output_id", "MISSING_OUTPUT_ID")
            raw_bindings = request.get("bindings")
            binding_evidence   = request.get("binding_evidence", {})
            injection_warnings = request.get("injection_warnings", [])
            verification_record = request.get("verification_record", {})
            if not self._loaded:
                raise RuntimeError("Gateway not initialised.")
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                bindings = self._validate_bindings(raw_bindings)
            except ValueError as exc:
                decision = self._build_decision("BLOCK",[{
                    "constraint_identity":"BINDING_VALIDATION",
                    "canonical_form":"N/A",
                    "actual_value":str(exc),
                    "expected":"All bindings must be 128‑bit signed integers with string keys"
                }], output_id, timestamp,
                    binding_evidence=binding_evidence,
                    injection_warnings=injection_warnings,
                    verification_record=verification_record)
                self._write_log(decision)
                return decision
            violations = self._evaluate_all(bindings)
            if self._review_queue:
                self._log_review_queue(output_id, timestamp)
            status = "ALLOW" if not violations else "BLOCK"
            decision = self._build_decision(status, violations, output_id, timestamp,
                                            binding_evidence=binding_evidence,
                                            injection_warnings=injection_warnings,
                                            verification_record=verification_record)
            self._write_log(decision)
            return decision
        except Exception as exc:
            output_id = "UNKNOWN"
            if isinstance(request, dict):
                output_id = request.get("output_id", "UNKNOWN")
            return self._unavailable_block(
                output_id=output_id,
                reason=f"gateway internal error: {type(exc).__name__}: {exc}"
            )

    def _unavailable_block(self, output_id: str, reason: str) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        violation = {
            "constraint_identity": "SYSTEM",
            "canonical_form":      "gateway must be available",
            "actual_value":        reason,
            "expected":            "gateway available and request valid"
        }
        payload = json.dumps({
            "status":     "GATEWAY_UNAVAILABLE",
            "violations": [violation],
            "output_id":  output_id,
            "timestamp":  timestamp,
        }, sort_keys=True)
        decision_id = hashlib.sha256(payload.encode()).hexdigest()
        decision = {
            "status":      "GATEWAY_UNAVAILABLE",
            "violations":  [violation],
            "decision_id": decision_id,
            "output_id":   output_id,
            "timestamp":   timestamp,
            "binding_evidence":   {},
            "injection_warnings": [],
            "verification_record": {"verified":[],"unverified":[],"mismatches":[],"source_errors":[]},
        }
        if self._gateway_private_key is not None:
            signing_payload = json.dumps({
                "decision_id": decision["decision_id"],
                "output_id":   decision["output_id"],
                "status":      decision["status"],
                "timestamp":   decision["timestamp"],
                "violations":  decision["violations"],
            }, sort_keys=True, separators=(",",":")).encode()
            decision["decision_signature"] = _sign(self._gateway_private_key, signing_payload)
        else:
            decision["decision_signature"] = None
        return decision

    # ── GAP‑36 + GAP‑42 + GAP‑44 enriched _build_decision ─────────────────
    def _build_decision(self, status, violations, output_id, timestamp,
                        binding_evidence=None,
                        injection_warnings=None,
                        verification_record=None,
                        personal_data_store=None):
        chain_violations = []
        for v in violations:
            actual_value = v.get("actual_value")
            if actual_value is not None and not isinstance(actual_value, str):
                value_hash = PersonalDataStore.compute_hash(int(actual_value))
                record_id = None
                if personal_data_store is not None:
                    record_id = personal_data_store.write(
                        decision_id   = f"{output_id}:{v.get('constraint_identity','')}",
                        variable_name = v.get("constraint_identity", "UNKNOWN"),
                        actual_value  = int(actual_value),
                    )
                chain_violation = {
                    "constraint_identity":      v.get("constraint_identity"),
                    "canonical_form":           v.get("canonical_form"),
                    "actual_value_hash":        value_hash,
                    "actual_value_erased":      False,
                    "personal_data_record_id":  record_id,
                    "expected":                 v.get("expected"),
                }
            else:
                chain_violation = dict(v)
            chain_violations.append(chain_violation)
        record_for_hash = {
            "status":     status,
            "violations": chain_violations,
            "output_id":  output_id,
            "timestamp":  timestamp,
        }
        canonical_json = json.dumps(record_for_hash, sort_keys=True, separators=(",", ":"))
        decision_id = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        decision = {
            "status":              status,
            "violations":          chain_violations,
            "decision_id":         decision_id,
            "output_id":           output_id,
            "timestamp":           timestamp,
            "binding_evidence":    binding_evidence   or {},
            "injection_warnings":  injection_warnings or [],
            "verification_record": verification_record or {
                "verified": [], "unverified": [], "mismatches": [], "source_errors": []
            },
            "gdpr_compliant":      True,
            "personal_data_store": "off-chain" if personal_data_store else "not_configured",
        }
        if self._gateway_private_key is not None:
            signing_payload = json.dumps({
                "decision_id": decision["decision_id"],
                "output_id":   decision["output_id"],
                "status":      decision["status"],
                "timestamp":   decision["timestamp"],
                "violations":  decision["violations"],
            }, sort_keys=True, separators=(",",":")).encode()
            decision["decision_signature"] = _sign(self._gateway_private_key, signing_payload)
        else:
            decision["decision_signature"] = None
        import json as _json, hashlib as _hashlib
        decision_hash_payload = _json.dumps({
            "constraint_commitment": getattr(self, '_commitment_id', 'UNSET'),
            "decision_id":           decision["decision_id"],
            "binding_values":        dict(sorted(
                {k: v["value"] for k, v in (binding_evidence or {}).items()}.items()
            )),
            "format_hashes":         dict(sorted(
                {k: v["format_hash"] for k, v in (binding_evidence or {}).items()}.items()
            )),
        }, sort_keys=True, separators=(",",":")).encode()
        decision["decision_hash"] = _hashlib.sha256(decision_hash_payload).hexdigest()
        return decision

    # ── GAP‑20 PATCH: _write_log uses AuditLog if configured ─────────────
    def _write_log(self, decision):
        prev_hash = self._decision_log[-1]["_chain_hash"] if self._decision_log else "GENESIS"
        chain_input = prev_hash + decision["decision_id"]
        chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        decision["_chain_hash"] = chain_hash
        self._decision_log.append(decision)
        if self._audit_log is not None:
            self._audit_log.append(decision)

    def _log_review_queue(self, output_id, timestamp):
        for item in self._review_queue:
            review_entry = {"event":"MANUAL_REVIEW_REQUIRED","output_id":output_id,"timestamp":timestamp,
                            "identity_string":item["identity_string"],"classification":item["classification"],
                            "reason":item["reason"]}
            chain_input = (self._decision_log[-1]["_chain_hash"] if self._decision_log else "GENESIS") + json.dumps(review_entry, sort_keys=True)
            chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
            review_entry["_chain_hash"] = chain_hash
            self._decision_log.append(review_entry)
            if self._audit_log is not None:
                self._audit_log.append(review_entry)

    @staticmethod
    def sanitise_for_model(decision):
        if decision["status"] == "ALLOW":
            reason = "Output satisfies all enforced constraints."
        else:
            count = len(decision["violations"])
            reason = f"Output blocked: {count} constraint violation{'s' if count != 1 else ''} detected."
        return {"status":decision["status"],"sanitised_reason":reason,"output_id":decision["output_id"],"decision_id":decision["decision_id"]}

    def get_decision_log(self):
        return list(self._decision_log)

    def verify_chain_integrity(self):
        previous_hash = "GENESIS"
        for entry in self._decision_log:
            stored = entry.get("_chain_hash")
            if "event" in entry:
                body = {k:v for k,v in entry.items() if k != "_chain_hash"}
                computed = hashlib.sha256((previous_hash + json.dumps(body, sort_keys=True)).encode("utf-8")).hexdigest()
            else:
                computed = hashlib.sha256((previous_hash + entry.get("decision_id","")).encode("utf-8")).hexdigest()
            if computed != stored: return False
            previous_hash = stored
        return True

    def get_review_queue(self):
        return list(self._review_queue)

# Minimal PersonalDataStore stub for Colab
try:
    PersonalDataStore
except NameError:
    class PersonalDataStore:
        @staticmethod
        def compute_hash(val): return hashlib.sha256(str(val).encode()).hexdigest()
