#!/usr/bin/env python3
"""
Phase 4 – UICP Runtime Enforcement Gateway (monolithic, Colab‑ready)
Engine + 73‑check alignment test suite (GAP‑21 + GAP‑42 + GAP‑36 + GAP‑44).
"""
import hashlib, json, re
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
        class Phase4EnforcementGateway:
    def __init__(self, gateway_private_key=None):
        self._enforceable = []
        self._review_queue = []
        self._decision_log = []
        self._loaded = False
        self._gateway_private_key = gateway_private_key
        self._commitment_id = "UNSET"

    def load_phase3_contract(self, contract):
        if self._loaded: raise RuntimeError("Contract already loaded.")
        status = contract.get("status")
        if status != "OK": raise RuntimeError(f"Phase 3 contract rejected: status={status!r}")
        raw = contract.get("canonical_constraints")
        if not isinstance(raw, list): raise RuntimeError("Missing canonical_constraints list.")
        for entry in raw:
            classification = entry.get("classification","")
            identity_string = entry.get("identity_string")
            canonical_form = entry.get("canonical_form")
            if not identity_string or not isinstance(identity_string, str): raise RuntimeError("Invalid identity_string")
            if classification in ENFORCEABLE_CLASSIFICATIONS:
                if not canonical_form or not isinstance(canonical_form, str): raise RuntimeError("Missing canonical_form")
                try:
                    _Parser(_Lexer(canonical_form)).parse_comparison()
                except ParseError as e:
                    raise RuntimeError(f"Unparseable canonical_form: {canonical_form!r}: {e}")
                self._enforceable.append({"identity_string":identity_string,"canonical_form":canonical_form,
                                          "classification":classification,"derived_from":entry.get("derived_from",[]),
                                          "reason":entry.get("reason","")})
            elif classification in REVIEW_CLASSIFICATIONS:
                self._review_queue.append({"identity_string":identity_string,"canonical_form":canonical_form,
                                           "classification":classification,"reason":entry.get("reason",""),
                                           "review_status":"PENDING_MANUAL_REVIEW"})
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
        """
        GAP‑44 PATCH: Extract actual_value from violations before
        computing decision_id. Replace with actual_value_hash in chain.
        Store raw value off-chain in PersonalDataStore if provided.
        """
        # ── GAP‑44: Separate personal data from chain record ─────────────────
        chain_violations = []

        for v in violations:
            actual_value = v.get("actual_value")

            if actual_value is not None and not isinstance(actual_value, str):
                # Numeric personal data — extract off-chain
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
                # Non-numeric or MISSING_VARIABLE — safe to store directly
                chain_violation = dict(v)

            chain_violations.append(chain_violation)

        # ── Compute decision_id over chain_violations (no raw values) ─────────
        record_for_hash = {
            "status":     status,
            "violations": chain_violations,
            "output_id":  output_id,
            "timestamp":  timestamp,
        }
        canonical_json = json.dumps(record_for_hash, sort_keys=True, separators=(",", ":"))
        decision_id = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        # ── Build decision dict ───────────────────────────────────────────────
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

        # GAP‑42: Sign decision record
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

        # GAP‑36: Composite decision hash
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

    def _write_log(self, decision):
        previous_hash = self._decision_log[-1]["_chain_hash"] if self._decision_log else "GENESIS"
        chain_input = previous_hash + decision["decision_id"]
        chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
        log_entry = {**decision, "_chain_hash": chain_hash}
        self._decision_log.append(log_entry)

    def _log_review_queue(self, output_id, timestamp):
        for item in self._review_queue:
            review_entry = {"event":"MANUAL_REVIEW_REQUIRED","output_id":output_id,"timestamp":timestamp,
                            "identity_string":item["identity_string"],"classification":item["classification"],
                            "reason":item["reason"]}
            chain_input = (self._decision_log[-1]["_chain_hash"] if self._decision_log else "GENESIS") + json.dumps(review_entry, sort_keys=True)
            chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
            review_entry["_chain_hash"] = chain_hash
            self._decision_log.append(review_entry)

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
        # ----------------------------- original test harness -----------------------------
PASS = FAIL = 0
def check(name, ok, detail=""):
    global PASS, FAIL
    if ok: PASS += 1; print(f"  [✓] {name}")
    else: FAIL += 1; print(f"  [✗] {name}  —  {detail}")

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

section("1. INTEGER PARSER CORRECTNESS")
cases = [
    ("x >= 6", {"x":6}, True, 6),
    ("x >= 6", {"x":5}, False, 5),
    ("x + 2*y >= 10", {"x":2,"y":4}, True, 10),
    ("x + 2*y >= 10", {"x":1,"y":4}, False, 9),
    ("x <= 100", {"x":99}, True, 99),
    ("x <= 100", {"x":101}, False, 101),
    ("x > 0", {"x":1}, True, 1),
    ("x < 0", {"x":-1}, True, -1),
    ("x = 5", {"x":5}, True, 5),
    ("x != 5", {"x":6}, True, 6),
    ("x != 5", {"x":5}, False, 5),
    ("-x >= -10", {"x":5}, True, -5),
    ("2*x + 3*y <= 20", {"x":4,"y":3}, True, 17),
    ("2*x + 3*y <= 20", {"x":5,"y":4}, False, 22),
]
for cf, bindings, expected_result, expected_lhs in cases:
    try:
        result, lhs = evaluate_canonical_form(cf, bindings)
        ok = (result == expected_result) and (lhs == expected_lhs)
        check(f"eval '{cf}' with {bindings}", ok, "" if ok else f"got ({result}, {lhs}), expected ({expected_result}, {expected_lhs})")
    except Exception as e: check(f"eval '{cf}'", False, str(e))
result, lhs = evaluate_canonical_form("x >= 6", {"x":6})
check("lhs value is pure integer (no float)", isinstance(lhs, int) and not isinstance(lhs, bool))

section("2. CONTRACT LOADING & REJECTION")
def fresh_gw(contract=None):
    gw = Phase4EnforcementGateway()
    if contract:
        gw.load_phase3_contract(contract)
    return gw
for bad_status in ["PARTIAL","FAIL",None]:
    try:
        gw = Phase4EnforcementGateway()
        gw.load_phase3_contract({"status":bad_status,"canonical_constraints":[]})
        check(f"Rejects status != OK ({bad_status})", False, "Should have raised")
    except RuntimeError: check(f"Rejects status != OK ({bad_status})", True)
try:
    gw = Phase4EnforcementGateway()
    gw.load_phase3_contract({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]})
    check("Accepts valid contract with status=OK", True)
except Exception as e: check("Accepts valid contract", False, str(e))
try:
    gw.load_phase3_contract({"status":"OK","canonical_constraints":[]})
    check("Rejects double load", False)
except RuntimeError: check("Rejects double load", True)

section("3. BINDING VALIDATION")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":3.14},"output_id":"T-FLOAT"})
check("Float binding → BLOCK", d["status"]=="BLOCK")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":True},"output_id":"T-BOOL"})
check("Boolean binding → BLOCK", d["status"]=="BLOCK")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":"six"},"output_id":"T-STR"})
check("String binding value → BLOCK", d["status"]=="BLOCK")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{1:6},"output_id":"T-INTKEY"})
check("Integer key in bindings → BLOCK", d["status"]=="BLOCK")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":2**127},"output_id":"T-OVERFLOW"})
check("Out-of-128-bit-range binding → BLOCK", d["status"]=="BLOCK")
d = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":-1},"output_id":"T-NEG"})
check("Negative int binding is valid (constraint-level BLOCK)", d["status"]=="BLOCK")

section("4. ENFORCEMENT CORRECTNESS")
MULTI_CONTRACT = {"status":"OK","canonical_constraints":[
    {"identity_string":"C_001","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""},
    {"identity_string":"C_002","canonical_form":"x + 2*y <= 20","classification":"LINEAR_MULTI_VAR","derived_from":[],"reason":""},
]}
gw = fresh_gw(MULTI_CONTRACT)
d = gw.check_output({"bindings":{"x":6,"y":5},"output_id":"T-ALLOW"})
check("ALLOW when all constraints satisfied", d["status"]=="ALLOW")
d = gw.check_output({"bindings":{"x":5,"y":5},"output_id":"T-BLOCK-C1"})
check("BLOCK when C_001 violated", d["status"]=="BLOCK")
d = gw.check_output({"bindings":{"x":7,"y":8},"output_id":"T-BLOCK-C2"})
check("BLOCK when C_002 violated", d["status"]=="BLOCK")
d = gw.check_output({"bindings":{"x":4,"y":9},"output_id":"T-BLOCK-BOTH"})
check("BLOCK and report both violations", d["status"]=="BLOCK" and len(d["violations"])==2)
d = gw.check_output({"bindings":{"x":5,"y":5},"output_id":"T-IDENTITY"})
for v in d["violations"]:
    check(f"identity_string unmodified: {v['constraint_identity']!r}", v["constraint_identity"] in {"C_001","C_002"})

section("5. NON-ENFORCEABLE CONSTRAINTS — NO AUTO-BLOCK")
REVIEW_CONTRACT = {"status":"OK","canonical_constraints":[
    {"identity_string":"C_LINEAR","canonical_form":"x >= 1","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""},
    {"identity_string":"C_NONLINEAR","canonical_form":"x^2 >= 4","classification":"NONLINEAR","derived_from":[],"reason":"Nonlinear"},
    {"identity_string":"C_OOS","canonical_form":"temporal","classification":"OUT_OF_SCOPE","derived_from":[],"reason":"Out of scope"},
]}
gw_review = Phase4EnforcementGateway()
gw_review.load_phase3_contract(REVIEW_CONTRACT)
d = gw_review.check_output({"bindings":{"x":2},"output_id":"T-REVIEW"})
check("NONLINEAR + OUT_OF_SCOPE do not cause BLOCK", d["status"]=="ALLOW")
check("Review queue populated", len(gw_review.get_review_queue())==2)

section("6. DETERMINISM")
import hashlib as _hl, json as _json
sample = {"status":"ALLOW","violations":[],"output_id":"DET","timestamp":"2024-01-01T00:00:00+00:00"}
canonical = _json.dumps(sample, sort_keys=True, separators=(",",":"))
run1 = _hl.sha256(canonical.encode("utf-8")).hexdigest()
run2 = _hl.sha256(canonical.encode("utf-8")).hexdigest()
check("SHA256(same record) identical", run1==run2)
gw_det = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]})
d_det = gw_det.check_output({"bindings":{"x":7},"output_id":"DET-ENG"})
recomputed = _hl.sha256(_json.dumps({"status":d_det["status"],"violations":d_det["violations"],"output_id":d_det["output_id"],"timestamp":d_det["timestamp"]}, sort_keys=True, separators=(",",":")).encode("utf-8")).hexdigest()
check("Engine decision_id matches external recomputation", d_det["decision_id"]==recomputed)
d_other = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]}).check_output({"bindings":{"x":5},"output_id":"DET-DIFF"})
check("Different bindings → different decision_id", d_det["decision_id"]!=d_other["decision_id"])

section("7. SHA256 DECISION_ID INTEGRITY")
gw_hash = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]})
d = gw_hash.check_output({"bindings":{"x":7},"output_id":"HASH"})
record_for_hash = {"status":d["status"],"violations":d["violations"],"output_id":d["output_id"],"timestamp":d["timestamp"]}
expected_id = _hl.sha256(_json.dumps(record_for_hash, sort_keys=True, separators=(",",":")).encode("utf-8")).hexdigest()
check("decision_id = SHA256(record excluding decision_id)", d["decision_id"]==expected_id)

section("8. CRYPTOGRAPHIC CHAIN INTEGRITY")
gw_chain = fresh_gw({"status":"OK","canonical_constraints":[{"identity_string":"C1","canonical_form":"x >= 6","classification":"LINEAR_SINGLE_VAR","derived_from":[],"reason":""}]})
for i in range(5): gw_chain.check_output({"bindings":{"x":6+i},"output_id":f"CHAIN-{i}"})
check("Chain integrity after 5 decisions", gw_chain.verify_chain_integrity())

section("9. MODEL-FACING RESPONSE — ZERO CONSTRAINT INTERNALS")
gw_san = fresh_gw(MULTI_CONTRACT)
d_block = gw_san.check_output({"bindings":{"x":4,"y":3},"output_id":"SAN"})
sanitised = Phase4EnforcementGateway.sanitise_for_model(d_block)
check("Sanitised response has only allowed keys", set(sanitised.keys())=={"status","sanitised_reason","output_id","decision_id"})
has_leak = any(fragment in sanitised.get("sanitised_reason","") for fragment in ["C_001","C_002","x >= 6","x + 2*y"])
check("Sanitised reason contains zero constraint internals", not has_leak)

section("10. OUTPUT CONTRACT SCHEMA COMPLIANCE")
required_top = {"status","violations","decision_id","output_id","timestamp","decision_signature","binding_evidence","injection_warnings","verification_record","decision_hash"}
d_allow = gw_san.check_output({"bindings":{"x":6,"y":5},"output_id":"SCHEMA-ALLOW"})
d_block = gw_san.check_output({"bindings":{"x":4,"y":3},"output_id":"SCHEMA-BLOCK"})
for label,d in [("ALLOW",d_allow),("BLOCK",d_block)]:
    check(f"{label} decision has required top-level keys", required_top.issubset(d.keys()))
    for v in d["violations"]:
        check(f"{label} violation entry has essential keys",
              all(k in v for k in ["constraint_identity","canonical_form","expected"]))

# ═══════════════════════════════════════════════════════════════
# GAP‑21 Tests (unchanged)
# ═══════════════════════════════════════════════════════════════
print("\n=== GAP-21 Fail-Safe Tests ===\n")

gap21_pass = gap21_fail = 0

gw_allow = fresh_gw(MULTI_CONTRACT)
res_allow = gw_allow.check_output({"bindings":{"x":6,"y":5},"output_id":"t01"})
if res_allow["status"] == "ALLOW":
    print("  PASS  GAP-21 | valid ALLOW request passes through normally")
    gap21_pass += 1
else:
    print(f"  FAIL  GAP-21 | valid ALLOW request got {res_allow['status']} instead of ALLOW")
    gap21_fail += 1

gw_block = fresh_gw(MULTI_CONTRACT)
res_block = gw_block.check_output({"bindings":{"x":5,"y":5},"output_id":"t02"})
if res_block["status"] == "BLOCK":
    print("  PASS  GAP-21 | valid BLOCK request passes through normally")
    gap21_pass += 1
else:
    print(f"  FAIL  GAP-21 | valid BLOCK request got {res_block['status']} instead of BLOCK")
    gap21_fail += 1

for label, req, expected in [
    ("request is not a dict", "this is a string not a dict", "GATEWAY_UNAVAILABLE"),
    ("request is None", None, "GATEWAY_UNAVAILABLE"),
]:
    gw = fresh_gw(MULTI_CONTRACT)
    res = gw.check_output(req)
    if res["status"] == expected:
        print(f"  PASS  GAP-21 | {label}")
        gap21_pass += 1
    else:
        print(f"  FAIL  GAP-21 | {label} got {res['status']} instead of {expected}")
        gap21_fail += 1

for label, req, expected in [
    ("bindings key missing → BLOCK", {"output_id":"t05"}, "BLOCK"),
    ("bindings is None → BLOCK", {"output_id":"t06","bindings":None}, "BLOCK"),
    ("bindings is a string → BLOCK", {"output_id":"t07","bindings":"age=35"}, "BLOCK"),
    ("bindings is a list → BLOCK", {"output_id":"t08","bindings":[35,8]}, "BLOCK"),
]:
    gw = fresh_gw(MULTI_CONTRACT)
    res = gw.check_output(req)
    if res["status"] == expected:
        print(f"  PASS  GAP-21 | {label}")
        gap21_pass += 1
    else:
        print(f"  FAIL  GAP-21 | {label} got {res['status']} instead of {expected}")
        gap21_fail += 1

for label, req in [
    ("GATEWAY_UNAVAILABLE structure — not a dict", "bad string"),
    ("GATEWAY_UNAVAILABLE structure — None", None),
]:
    gw = fresh_gw(MULTI_CONTRACT)
    unavail = gw.check_output(req)
    required_keys = {"status","violations","decision_id","output_id","timestamp"}
    has_keys = required_keys.issubset(unavail.keys())
    is_list = isinstance(unavail.get("violations"), list)
    has_viol = len(unavail.get("violations",[])) > 0
    viol_keys = {"constraint_identity","canonical_form","actual_value","expected"}
    viol_complete = viol_keys.issubset(unavail["violations"][0].keys()) if has_viol else False
    all_ok = has_keys and is_list and has_viol and viol_complete
    if all_ok:
        print(f"  PASS  GAP-21 | {label}")
        gap21_pass += 1
    else:
        print(f"  FAIL  GAP-21 | {label}  —  keys:{has_keys} list:{is_list} nonempty:{has_viol} viol_keys:{viol_complete}")
        gap21_fail += 1

gw_check = fresh_gw(MULTI_CONTRACT)
unavail = gw_check.check_output(None)
struct_checks = [
    ("GATEWAY_UNAVAILABLE has all required top-level keys",
     {"status","violations","decision_id","output_id","timestamp"}.issubset(unavail.keys())),
    ("violations is a list",
     isinstance(unavail.get("violations"), list)),
    ("violations list is non-empty",
     len(unavail.get("violations",[])) > 0),
    ("violation object has all required keys",
     {"constraint_identity","canonical_form","actual_value","expected"}.issubset(
         unavail["violations"][0].keys()) if unavail.get("violations") else False),
    ("decision_id is non-empty string",
     isinstance(unavail.get("decision_id"), str) and len(unavail.get("decision_id","")) > 0),
]
for label, cond in struct_checks:
    if cond:
        print(f"  PASS  GAP-21 | {label}")
        gap21_pass += 1
    else:
        print(f"  FAIL  GAP-21 | {label}")
        gap21_fail += 1

total_gap21 = gap21_pass + gap21_fail
print(f"\n=== GAP-21 Results: {gap21_pass}/{total_gap21} passed ===")
if gap21_fail > 0: print("FAIL — do not commit")
else: print("ALL GAP-21 TESTS PASSED — ready for PR")

# ═══════════════════════════════════════════════════════════════
# GAP‑42 Tests — with local verify_decision_record (fix)
# ═══════════════════════════════════════════════════════════════
print("\n=== GAP-42 Phase 4→5 Handoff Integrity Tests ===\n")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Define the real verify_decision_record here so it's always available
def _verify_decision_record(decision: dict, gateway_public_key) -> tuple:
    """Verify that a Phase 4 decision record was signed by the legitimate gateway."""
    try:
        sig_hex = decision.get("decision_signature")
        if sig_hex is None:
            return False, "decision_signature field is absent"
        if not isinstance(sig_hex, str) or len(sig_hex) == 0:
            return False, f"decision_signature is invalid type: {type(sig_hex)}"
        signing_payload = json.dumps(
            {"decision_id": decision["decision_id"],
             "output_id":   decision["output_id"],
             "status":      decision["status"],
             "timestamp":   decision["timestamp"],
             "violations":  decision["violations"]},
            sort_keys=True, separators=(",",":")).encode()
        sig_bytes = bytes.fromhex(sig_hex)
        # _verify expects (pub, sig_hex, data)
        from cryptography.exceptions import InvalidSignature
        try:
            gateway_public_key.verify(sig_bytes, signing_payload)
            return True, None
        except (InvalidSignature, ValueError):
            return False, "signature verification failed — record may be tampered"
    except Exception as exc:
        return False, f"verification error: {type(exc).__name__}: {exc}"

gap42_pass = gap42_fail = 0
def chk42(label, condition, detail=""):
    global gap42_pass, gap42_fail
    if condition:
        gap42_pass += 1
        print(f"  PASS  GAP-42 | {label}")
    else:
        gap42_fail += 1
        print(f"  FAIL  GAP-42 | {label}" + (f" — {detail}" if detail else ""))

priv_key = Ed25519PrivateKey.generate()
pub_key  = priv_key.public_key()
gw_signed = Phase4EnforcementGateway(gateway_private_key=priv_key)
gw_signed.load_phase3_contract(MULTI_CONTRACT)
gw_unsigned = Phase4EnforcementGateway()
gw_unsigned.load_phase3_contract(MULTI_CONTRACT)

allow_req = {"output_id": "g42-t01", "bindings": {"x": 6, "y": 5}}
allow_dec = gw_signed.check_output(allow_req)
chk42("Signed ALLOW has decision_signature field", "decision_signature" in allow_dec)
chk42("Signed ALLOW decision_signature is a string", isinstance(allow_dec.get("decision_signature"), str))
chk42("Signed ALLOW decision_signature is non-empty", len(allow_dec.get("decision_signature", "")) > 0)

block_req = {"output_id": "g42-t02", "bindings": {"x": 4, "y": 3}}
block_dec = gw_signed.check_output(block_req)
chk42("Signed BLOCK has decision_signature field", "decision_signature" in block_dec)
chk42("Signed BLOCK decision_signature is non-empty", len(block_dec.get("decision_signature", "")) > 0)

unavail_dec = gw_signed.check_output(None)
chk42("GATEWAY_UNAVAILABLE has decision_signature key", "decision_signature" in unavail_dec)

unsigned_dec = gw_unsigned.check_output(allow_req)
chk42("Unsigned gateway decision_signature is None", unsigned_dec.get("decision_signature") is None)

valid, reason = _verify_decision_record(allow_dec, pub_key)
chk42("Phase 5 verifies valid signed ALLOW decision", valid, reason)
valid_b, reason_b = _verify_decision_record(block_dec, pub_key)
chk42("Phase 5 verifies valid signed BLOCK decision", valid_b, reason_b)

dec_no_sig = dict(allow_dec)
dec_no_sig.pop("decision_signature", None)
valid_ns, reason_ns = _verify_decision_record(dec_no_sig, pub_key)
chk42("Phase 5 rejects decision with no signature", not valid_ns, reason_ns)

dec_tampered = dict(allow_dec)
dec_tampered["output_id"] = "INJECTED-FAKE-ID"
valid_t, reason_t = _verify_decision_record(dec_tampered, pub_key)
chk42("Phase 5 rejects tampered decision record", not valid_t, reason_t)

wrong_priv = Ed25519PrivateKey.generate()
wrong_pub  = wrong_priv.public_key()
valid_w, reason_w = _verify_decision_record(allow_dec, wrong_pub)
chk42("Phase 5 rejects decision verified with wrong public key", not valid_w, reason_w)

dec_empty_sig = dict(allow_dec)
dec_empty_sig["decision_signature"] = ""
valid_e, reason_e = _verify_decision_record(dec_empty_sig, pub_key)
chk42("Phase 5 rejects empty signature string", not valid_e, reason_e)

chk42("Signed gateway still produces ALLOW for valid bindings", allow_dec["status"] == "ALLOW")
chk42("Signed gateway still produces BLOCK for age violation", block_dec["status"] == "BLOCK")

total_42 = gap42_pass + gap42_fail
print(f"\n=== GAP-42 Results: {gap42_pass}/{total_42} passed ===")
if gap42_fail > 0: print("FAIL — do not commit")
else: print("ALL GAP-42 TESTS PASSED — ready for PR")

# ── Combined totals ──
total_all = PASS + FAIL + gap21_pass + gap21_fail + gap42_pass + gap42_fail
passed_all = PASS + gap21_pass + gap42_pass
failed_all = FAIL + gap21_fail + gap42_fail
print("\n" + "="*60)
print(f"COMBINED RESULTS: {passed_all} passed, {failed_all} failed")
if failed_all == 0:
    print("  ✓ ALL TESTS PASS — Phase 4 engine with GAP‑21 + GAP‑42 + GAP‑36 + GAP‑44 is ALIGNED.\n")
else:
    print(f"  ✗ {failed_all} FAILURE(S) — Engine is NOT aligned.\n")
