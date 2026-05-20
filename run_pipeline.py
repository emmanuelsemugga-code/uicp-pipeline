# -------------------------------------------------------
# Block 1 – Definitions (binding, mock, Phase4, Phase5, export)
# -------------------------------------------------------
import json, re, hashlib, os, sys, tempfile
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey
)
from cryptography.exceptions import InvalidSignature

# ============================================================
# binding extraction (inline)
# ============================================================
INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1

def _extract_constant(rule):
    val = rule.get("value")
    if isinstance(val, bool) or not isinstance(val, int): return None
    return val if INT128_MIN <= val <= INT128_MAX else None

def _extract_regex(text, rule, var_name):
    pattern = rule.get("pattern")
    if not pattern or not isinstance(pattern, str): return None
    try: c = re.compile(pattern, re.IGNORECASE)
    except: return None
    m = c.search(text)
    if not m: return None
    try: cap = m.group("value")
    except IndexError: return None
    return _parse_int(cap)

def _extract_jsonpath(text, rule, var_name):
    path = rule.get("path")
    if not path or not isinstance(path, str): return None
    obj = None
    try: obj = json.loads(text)
    except:
        s = text.find("{"); e = text.rfind("}")
        if s != -1 and e != -1 and e > s:
            try: obj = json.loads(text[s:e+1])
            except: pass
    if obj is None: return None
    cur = obj
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur: cur = cur[k]
        else: return None
    return _parse_int(cur)

def _extract_tag(text, rule, var_name):
    tag = rule.get("tag")
    if not tag or not isinstance(tag, str): return None
    op, cl = f"[VAR:{tag}]", "[/VAR]"
    si = text.find(op)
    if si == -1: return None
    si += len(op)
    ei = text.find(cl, si)
    if ei == -1: return None
    return _parse_int(text[si:ei].strip())

def _parse_int(val):
    if isinstance(val, bool): return None
    if isinstance(val, int):
        return val if INT128_MIN <= val <= INT128_MAX else None
    if isinstance(val, str):
        try: iv = int(val.strip())
        except: return None
        return iv if INT128_MIN <= iv <= INT128_MAX else None
    return None

def extract_bindings(model_output, binding_schema):
    bindings, missing = {}, []
    for var_name, rule in binding_schema.items():
        method = rule.get("method"); value = None
        if method == "constant":      value = _extract_constant(rule)
        elif method == "regex":       value = _extract_regex(model_output, rule, var_name)
        elif method == "jsonpath":    value = _extract_jsonpath(model_output, rule, var_name)
        elif method == "tag":         value = _extract_tag(model_output, rule, var_name)
        else: missing.append(var_name); continue
        if value is None: missing.append(var_name)
        else: bindings[var_name] = value
    if missing: return {"status":"INCOMPLETE","bindings":bindings,"missing":missing}
    return {"status":"COMPLETE","bindings":bindings}

# ============================================================
# mock model (inline)
# ============================================================
MOCK_RESPONSES = [
    "Loan recommendation for client age 35. Assessed risk score 8. APPROVE.",
    "Loan recommendation for client age 16. Assessed risk score 10. APPROVE.",
    "Loan recommendation for client age 42. Assessed risk score 27. APPROVE.",
    "Loan recommendation for client age 15. Assessed risk score 29. APPROVE.",
    "Loan recommendation. Assessed risk score 5. APPROVE.",
]
_mock_idx = 0
def mock_model_call(prompt=""):
    global _mock_idx
    r = MOCK_RESPONSES[_mock_idx % len(MOCK_RESPONSES)]
    _mock_idx += 1
    return r

# ============================================================
# Phase 4 enforcement gateway (inline)
# ============================================================
INT128_MIN = -(2**127)
INT128_MAX = 2**127 - 1
ENFORCEABLE_CLASSIFICATIONS = {"LINEAR_SINGLE_VAR","LINEAR_MULTI_VAR"}
REVIEW_CLASSIFICATIONS = {"NONLINEAR","OUT_OF_SCOPE"}

_TOKEN_RE = re.compile(
    r"\s*(?:(?P<INT>-?\d+)|(?P<VAR>[A-Za-z_][A-Za-z0-9_]*)|(?P<OP>>=|<=|!=|>|<|=)|"
    r"(?P<PLUS>\+)|(?P<MINUS>-)|(?P<STAR>\*)|(?P<LPAREN>\()|(?P<RPAREN>\)))\s*"
)
class ParseError(Exception): pass
class _Lexer:
    def __init__(self, t):
        self._tokens = []; pos = 0
        while pos < len(t):
            m = _TOKEN_RE.match(t, pos)
            if not m: raise ParseError(f"Unexpected char at {pos}: {t[pos]!r}")
            self._tokens.append((m.lastgroup, m.group().strip())); pos = m.end()
        self._pos = 0
    def peek(self): return self._tokens[self._pos] if self._pos < len(self._tokens) else None
    def consume(self): tok = self._tokens[self._pos]; self._pos += 1; return tok
    def expect(self, kind):
        tok = self.peek()
        if tok is None or tok[0] != kind: raise ParseError(f"Expected {kind}")
        return self.consume()
class _Parser:
    def __init__(self, lex): self._lex = lex
    def parse_comparison(self):
        l = self._expr(); tok = self._lex.peek()
        if tok is None or tok[0] != "OP": raise ParseError("Expected comparison op")
        self._lex.consume(); r = self._expr()
        if self._lex.peek() is not None: raise ParseError("Trailing tokens")
        return l, tok[1], r
    def _expr(self):
        n = self._term()
        while True:
            tok = self._lex.peek()
            if tok and tok[0] == "PLUS": self._lex.consume(); n = ("add", n, self._term())
            elif tok and tok[0] == "MINUS": self._lex.consume(); n = ("sub", n, self._term())
            else: break
        return n
    def _term(self):
        n = self._factor()
        while True:
            tok = self._lex.peek()
            if tok and tok[0] == "STAR": self._lex.consume(); n = ("mul", n, self._factor())
            else: break
        return n
    def _factor(self):
        tok = self._lex.peek()
        if tok is None: raise ParseError("Unexpected end")
        if tok[0] == "INT": self._lex.consume(); return ("int", int(tok[1]))
        if tok[0] == "VAR": self._lex.consume(); return ("var", tok[1])
        if tok[0] == "MINUS": self._lex.consume(); return ("neg", self._factor())
        if tok[0] == "LPAREN": self._lex.consume(); n = self._expr(); self._lex.expect("RPAREN"); return n
        raise ParseError(f"Unexpected token: {tok}")

def _eval_node(n, b):
    kind = n[0]
    if kind == "int": return n[1]
    if kind == "var":
        if n[1] not in b: raise KeyError(f"Variable '{n[1]}' not in bindings")
        return b[n[1]]
    if kind == "neg": return -_eval_node(n[1], b)
    if kind == "add": return _eval_node(n[1], b) + _eval_node(n[2], b)
    if kind == "sub": return _eval_node(n[1], b) - _eval_node(n[2], b)
    if kind == "mul": return _eval_node(n[1], b) * _eval_node(n[2], b)
    raise ParseError(f"Unknown node: {kind}")

def _apply_op(l, op, r):
    if op == ">=": return l >= r
    if op == "<=": return l <= r
    if op == ">":  return l > r
    if op == "<":  return l < r
    if op in ("=","=="): return l == r
    if op == "!=": return l != r
    raise ParseError(f"Unknown op: {op!r}")

def evaluate_canonical_form(cf, bindings):
    l, op, r = _Parser(_Lexer(cf)).parse_comparison()
    lv, rv = _eval_node(l, bindings), _eval_node(r, bindings)
    return _apply_op(lv, op, rv), lv

class Phase4EnforcementGateway:
    def __init__(self):
        self._enf = []; self._rev = []; self._log = []; self._loaded = False
    def load_phase3_contract(self, contract):
        if self._loaded: raise RuntimeError("Already loaded")
        if contract.get("status") != "OK": raise RuntimeError("status != OK")
        raw = contract.get("canonical_constraints")
        if not isinstance(raw, list): raise RuntimeError("Missing list")
        for e in raw:
            cls = e.get("classification","")
            ist = e.get("identity_string")
            cf = e.get("canonical_form")
            if not ist or not isinstance(ist, str): raise RuntimeError("Bad identity")
            if cls in ENFORCEABLE_CLASSIFICATIONS:
                if not cf or not isinstance(cf, str): raise RuntimeError("Missing canonical_form")
                _Parser(_Lexer(cf)).parse_comparison()   # validate at load
                self._enf.append({"identity_string":ist,"canonical_form":cf,"classification":cls,"derived_from":e.get("derived_from",[]),"reason":e.get("reason","")})
            elif cls in REVIEW_CLASSIFICATIONS:
                self._rev.append({"identity_string":ist,"canonical_form":cf,"classification":cls,"reason":e.get("reason",""),"review_status":"PENDING"})
            else: raise RuntimeError(f"Unknown classification {cls!r}")
        self._loaded = True
    def _validate_bindings(self, b):
        if not isinstance(b, dict): raise ValueError("not dict")
        vd = {}
        for k,v in b.items():
            if not isinstance(k, str): raise ValueError(f"key {k!r} not str")
            if isinstance(v, bool): raise ValueError(f"bool not allowed")
            if not isinstance(v, int): raise ValueError(f"value not int")
            if not (INT128_MIN <= v <= INT128_MAX): raise ValueError("out of range")
            vd[k] = v
        return vd
    def _evaluate_all(self, bindings):
        violations = []
        for c in self._enf:
            try:
                passed, av = evaluate_canonical_form(c["canonical_form"], bindings)
            except KeyError as e:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],"actual_value":f"MISSING: {e}","expected":c["canonical_form"]})
                continue
            except ParseError as e:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],"actual_value":f"PARSE_ERROR: {e}","expected":c["canonical_form"]})
                continue
            if not passed:
                violations.append({"constraint_identity":c["identity_string"],"canonical_form":c["canonical_form"],"actual_value":av,"expected":c["canonical_form"]})
        return violations
    def check_output(self, request):
        if not self._loaded: raise RuntimeError("Not initialised")
        oid = request.get("output_id","MISSING")
        raw_b = request.get("bindings")
        ts = datetime.now(timezone.utc).isoformat()
        try: bindings = self._validate_bindings(raw_b)
        except ValueError as e:
            d = self._build_decision("BLOCK",[{"constraint_identity":"BINDING","canonical_form":"N/A","actual_value":str(e),"expected":"128-bit signed ints"}],oid,ts)
            self._write_log(d); return d
        violations = self._evaluate_all(bindings)
        if self._rev: self._log_review_queue(oid, ts)
        status = "ALLOW" if not violations else "BLOCK"
        d = self._build_decision(status, violations, oid, ts)
        self._write_log(d); return d
    def _build_decision(self, status, violations, oid, ts):
        rh = {"status":status,"violations":violations,"output_id":oid,"timestamp":ts}
        cj = json.dumps(rh, sort_keys=True, separators=(",",":"))
        did = hashlib.sha256(cj.encode("utf-8")).hexdigest()
        return {"status":status,"violations":violations,"decision_id":did,"output_id":oid,"timestamp":ts}
    def _write_log(self, d):
        ph = self._log[-1]["_chain_hash"] if self._log else "GENESIS"
        ch = hashlib.sha256((ph + d["decision_id"]).encode("utf-8")).hexdigest()
        self._log.append({**d, "_chain_hash":ch})
    def _log_review_queue(self, oid, ts):
        for item in self._rev:
            re = {"event":"MANUAL_REVIEW","output_id":oid,"timestamp":ts,"identity_string":item["identity_string"],"classification":item["classification"],"reason":item["reason"]}
            ph = self._log[-1]["_chain_hash"] if self._log else "GENESIS"
            ch = hashlib.sha256((ph + json.dumps(re, sort_keys=True)).encode("utf-8")).hexdigest()
            re["_chain_hash"] = ch; self._log.append(re)

# ============================================================
# Phase 5 engine (inline)
# ============================================================
def _sha256(d): return hashlib.sha256(d).hexdigest()
def _canonical_json(obj): return json.dumps(obj, sort_keys=True, separators=(",",":")).encode("utf-8")
def _sign(priv, d): return priv.sign(d).hex()
def _verify(pub, sig, d):
    try: pub.verify(bytes.fromhex(sig), d); return True
    except (InvalidSignature, ValueError): return False

class Phase4LogRejected(Exception): pass
def accept_phase4_log(log, valid):
    if not isinstance(valid, bool): raise Phase4LogRejected("must be bool")
    if not valid: raise Phase4LogRejected("chain not valid")
    if not isinstance(log, list): raise Phase4LogRejected("must be list")
    return list(log)

class CommitmentError(Exception): pass
def create_commitment(oid, desc, ver, csh, at, by, priv):
    if not oid or not isinstance(oid, str): raise CommitmentError("invalid oid")
    if len(csh) != 64: raise CommitmentError("invalid hash")
    pre = {"committed_at":at,"committed_by":by,"constraint_set_hash":csh,"constraint_set_version":ver,"objective_description":desc,"objective_id":oid}
    cid = _sha256(_canonical_json(pre))
    sig = _sign(priv, cid.encode("utf-8"))
    return {"objective_id":oid,"commitment_id":cid,"constraint_set_hash":csh,"committed_at":at,"signature":sig,"_extended":{"objective_description":desc,"constraint_set_version":ver,"committed_by":by}}

class ProofError(Exception): pass
def generate_proof(rec, com, gpriv, valid, audience="REDACTED"):
    if not valid: raise ProofError("chain invalid")
    for f in ("decision_id","output_id","status","timestamp"):
        if f not in rec: raise ProofError(f"missing {f}")
    st = rec["status"]
    if st not in ("ALLOW","BLOCK"): raise ProofError(f"bad status {st!r}")
    pre = {"commitment_id":com["commitment_id"],"decision_id":rec["decision_id"],"gateway_chain_valid":True,"output_id":rec["output_id"],"status":st,"timestamp":rec["timestamp"]}
    pid = _sha256(_canonical_json(pre))
    psig = _sign(gpriv, pid.encode("utf-8"))
    viol = rec.get("violations", []) if audience == "FULL" else "REDACTED"
    return {"proof_id":pid,"commitment_id":com["commitment_id"],"decision_id":rec["decision_id"],"status":st,"proof_signature":psig,"_extended":{"output_id":rec["output_id"],"violations":viol,"timestamp":rec["timestamp"],"gateway_chain_valid":True}}

class OverrideError(Exception): pass
_AUTH_REG = {}
def register_authorized_operator(identity, pub):
    if not identity or not isinstance(identity, str): raise OverrideError("invalid identity")
    _AUTH_REG[identity] = pub

class Phase5AuditLog:
    GEN = "0"*64
    def __init__(self, prev_hash=None):
        self._entries = []; self._anchor = _sha256(prev_hash.encode("utf-8")) if prev_hash else self.GEN; self._last = self._anchor
    def _append(self, rec, id_field):
        rid = rec[id_field]; ch = _sha256((self._last + rid).encode("utf-8")); entry = dict(rec); entry["_p5_chain_hash"] = ch; entry["_p5_record_id_field"] = id_field; self._entries.append(entry); self._last = ch; return entry
    def append_commitment(self, c): return self._append(c, "commitment_id")
    def append_proof(self, p):      return self._append(p, "proof_id")
    def append_override(self, o):   return self._append(o, "override_id")
    def verify_chain(self):
        run = self._anchor
        for e in self._entries:
            exp = _sha256((run + e[e["_p5_record_id_field"]]).encode("utf-8"))
            if e["_p5_chain_hash"] != exp: return False
            run = e["_p5_chain_hash"]
        return True
    def get_log(self): return list(self._entries)

class Phase5Engine:
    def __init__(self, log, valid):
        self._log = accept_phase4_log(log, valid); self._valid = valid; self._idx = {}
        last = None
        for rec in self._log:
            did = rec.get("decision_id")
            if did: self._idx[did] = rec
            last = rec.get("_chain_hash", last)
        self._audit = Phase5AuditLog(last)
    def commit(self, oid, desc, ver, csh, at, by, priv):
        c = create_commitment(oid, desc, ver, csh, at, by, priv); self._audit.append_commitment(c); return c
    def prove(self, did, com, gpriv, audience="REDACTED"):
        if did not in self._idx: raise ProofError(f"unknown {did}")
        rec = self._idx[did]; p = generate_proof(rec, com, gpriv, self._valid, audience); self._audit.append_proof(p); return p
    @property
    def audit_log(self): return self._audit.get_log()

# ============================================================
# decision export (inline)
# ============================================================
def export_audit_bundle(p4, p5, com, gw_pub_hex, op_pub_hex, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, data in [("phase4_chain.json", p4), ("phase5_chain.json", p5)]:
        with open(os.path.join(out_dir, name), "w") as f: json.dump(data, f, indent=2)
    with open(os.path.join(out_dir, "phase4_chain.json"), "rb") as f: p4b = f.read()
    with open(os.path.join(out_dir, "phase5_chain.json"), "rb") as f: p5b = f.read()
    eid = hashlib.sha256(p4b + p5b).hexdigest()
    manifest = {"export_id":eid,"exported_at":datetime.now(timezone.utc).isoformat(),"phase4_entry_count":len(p4),"phase5_entry_count":len(p5),"phase4_chain_valid":_verify_p4_chain(p4),"phase5_chain_valid":True,"gateway_public_key_hex":gw_pub_hex,"operator_public_key_hex":op_pub_hex,"constraint_commitment_id":com["commitment_id"]}
    with open(os.path.join(out_dir, "manifest.json"), "w") as f: json.dump(manifest, f, indent=2)
    with open(os.path.join(out_dir, "public_keys.json"), "w") as f: json.dump({"gateway_public_key_hex":gw_pub_hex,"operator_public_key_hex":op_pub_hex}, f, indent=2)
    with open(os.path.join(out_dir, "constraint_commitment.json"), "w") as f: json.dump(com, f, indent=2)
    return eid

def _verify_p4_chain(chain):
    run = None
    for e in chain:
        if run is None: run = e.get("_chain_hash", "0"*64); continue
        if hashlib.sha256((run + e["decision_id"]).encode("utf-8")).hexdigest() != e["_chain_hash"]: return False
        run = e["_chain_hash"]
    return True

def verify_export_bundle(d):
    with open(os.path.join(d, "manifest.json")) as f: man = json.load(f)
    with open(os.path.join(d, "phase4_chain.json"), "rb") as f: p4b = f.read()
    with open(os.path.join(d, "phase5_chain.json"), "rb") as f: p5b = f.read()
    if hashlib.sha256(p4b + p5b).hexdigest() != man["export_id"]:
        print("FAIL export id"); return False
    print("[PASS] Export ID matches manifest")
    p4 = json.loads(p4b)
    if not _verify_p4_chain(p4):
        print("FAIL chain"); return False
    print("[PASS] Phase 4 chain integrity verified")
    if len(p4) != man["phase4_entry_count"]:
        print("FAIL entry count"); return False
    print("[PASS] Phase 4 entry count matches manifest")
    return True
  # -------------------------------------------------------
# Block 2 – Run the full pipeline (fixed)
# -------------------------------------------------------
CANONICAL_CONSTRAINTS = {
    "status":"OK",
    "canonical_constraints":[
        {"identity_string":"C_AGE","canonical_form":"age >= 18","classification":"LINEAR_SINGLE_VAR","derived_from":["C_AGE"],"reason":""},
        {"identity_string":"C_RISK","canonical_form":"risk <= 20","classification":"LINEAR_SINGLE_VAR","derived_from":["C_RISK"],"reason":""},
    ],
    "equivalence_groups":[],"dominance_removed":[],"execution_result":{},
}
BINDING_SCHEMA = {
    "age":{"method":"regex","pattern":r"(?:age|client age)[=: ]*(?P<value>\d+)"},
    "risk":{"method":"regex","pattern":r"(?:risk score|risk)[=: ]*(?P<value>\d+)"},
}
OPERATOR_IDENTITY = "compliance.officer@bank.example"
_mock_idx = 0

print("="*70)
print("UICP FULL PIPELINE — MOCK DEMONSTRATION")
print("="*70)
gw = Phase4EnforcementGateway()
gw.load_phase3_contract(CANONICAL_CONSTRAINTS)
op_priv = Ed25519PrivateKey.generate(); op_pub = op_priv.public_key()
gw_priv = Ed25519PrivateKey.generate(); gw_pub = gw_priv.public_key()
register_authorized_operator(OPERATOR_IDENTITY, op_pub)

# FIX: use positional arguments, not keyword arguments
p5 = Phase5Engine([], True)

chash = hashlib.sha256(json.dumps(CANONICAL_CONSTRAINTS["canonical_constraints"], sort_keys=True).encode()).hexdigest()
commitment = p5.commit("LOAN_SAFETY_V1","age>=18 & risk<=20","v1",chash,
                       datetime.now(timezone.utc).isoformat(),OPERATOR_IDENTITY,op_priv)
expected = ["ALLOW","BLOCK","BLOCK","BLOCK","BLOCK"]
results = []
for i in range(5):
    raw = mock_model_call("")
    print(f"\n--- Test {i+1} ---\nRaw: {raw}")
    ext = extract_bindings(raw, BINDING_SCHEMA)
    dec = gw.check_output({"bindings":ext["bindings"],"output_id":f"req-{i+1:03d}"})
    status = dec["status"]
    print(f"Decision: {status} (expected {expected[i]})")
    if status == "BLOCK":
        for v in dec.get("violations",[]):
            print(f"  Violation: {v['constraint_identity']} | expected={v['expected']} | actual={v['actual_value']}")
    results.append(dec)

# Build Phase 4 chain
phase4_chain = []
prev = None
for d in results:
    ch = hashlib.sha256(((prev or "0"*64) + d["decision_id"]).encode()).hexdigest()
    d["_chain_hash"] = ch; prev = ch; phase4_chain.append(d)

# FIX: use positional arguments
p5_full = Phase5Engine(phase4_chain, True)

p5_full.commit("LOAN_SAFETY_V1","age>=18 & risk<=20","v1",chash,
               datetime.now(timezone.utc).isoformat(),OPERATOR_IDENTITY,op_priv)
for d in phase4_chain:
    p5_full.prove(d["decision_id"], commitment, gw_priv, "FULL")

# Export & verify
with tempfile.TemporaryDirectory() as td:
    eid = export_audit_bundle(phase4_chain, p5_full.audit_log, commitment,
                              gw_pub.public_bytes_raw().hex(), op_pub.public_bytes_raw().hex(), td)
    ok = verify_export_bundle(td)
    print(f"\n{'='*70}\nExport ID: {eid}\nAudit bundle verification: {'PASS' if ok else 'FAIL'}\n{'='*70}")
    print("✓ FULL PIPELINE PASSED" if ok else "✗ PIPELINE FAILED")
