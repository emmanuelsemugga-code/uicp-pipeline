#!/usr/bin/env python3
"""
phase3_engine.py – UICP Phase 3 Canonicalization & Satisfiability
Real Phase 1 identity strings.  All arithmetic exact (Fraction).
"""
import json, re, hashlib, sys, copy
from fractions import Fraction
from itertools import combinations
from collections import defaultdict
from typing import Any

class LinearConstraint:
    def __init__(self, identity_string, coeffs, op, rhs, classification="LINEAR_MULTI_VAR",
                 derived_from=None, reason=""):
        self.identity_string = identity_string
        self.original_coeffs = dict(coeffs)
        self.original_op = op
        self.original_rhs = rhs
        self.classification = classification
        self.derived_from = derived_from if derived_from else [identity_string]
        self.reason = reason
        self.norm_coeffs, self.norm_rhs = self._normalize(coeffs, op, rhs)

    @staticmethod
    def _normalize(coeffs, op, rhs):
        c = dict(coeffs)
        r = rhs
        if op in (">=", ">"):
            if op == ">":
                r = r + Fraction(1)
        elif op in ("<=", "<"):
            c = {v: -cv for v, cv in c.items()}
            r = -rhs
            if op == "<":
                r = r + Fraction(1)
        return c, r

    def canonical_key(self):
        vars_sorted = sorted(self.norm_coeffs.keys())
        nums = [int(self.norm_coeffs[v].numerator) for v in vars_sorted
                if self.norm_coeffs.get(v, Fraction(0)) != 0]
        nums.append(int(self.norm_rhs.numerator))
        from math import gcd
        g = 0
        for n in nums: g = gcd(g, abs(n))
        if g == 0: g = 1
        scaled = tuple((v, self.norm_coeffs.get(v, Fraction(0)) / g)
                       for v in vars_sorted if self.norm_coeffs.get(v, Fraction(0)) != 0)
        return (scaled, self.norm_rhs / g)

def looks_nonlinear(identity_string):
    if re.search(r'\bpow\b|\bsqrt\b|\bexp\b|\blog\b|\bsin\b|\bcos\b|\btan\b|\^',
                  identity_string, re.IGNORECASE):
        return True
    mul_pattern = re.compile(r'"?\*"?\s*,\s*(\[.*?\])\s*,\s*(\[.*?\])', re.DOTALL)
    for m in mul_pattern.finditer(identity_string):
        left, right = m.group(1), m.group(2)
        if '"var"' in left and '"var"' in right:
            return True
    return False

def classify_out_of_scope(c):
    istr = c["identity_string"]
    if looks_nonlinear(istr):
        return {"identity_string": istr, "canonical_form": istr,
                "classification": "NONLINEAR", "derived_from": [istr],
                "reason": "Constraint contains nonlinear structure."}
    return {"identity_string": istr, "canonical_form": istr,
            "classification": "OUT_OF_SCOPE", "derived_from": [istr],
            "reason": c.get("reason", "Unsupported structure.")}

def parse_phase2_output(raw):
    if not isinstance(raw, dict): raise ValueError("not dict")
    if raw.get("status") != "OK": raise ValueError("status not OK")
    return raw

def build_linear_constraint_from_phase2(c):
    return LinearConstraint(c["identity_string"], {c["var"]: Fraction(1)},
                            c["op"], Fraction(c["value"]), "LINEAR_SINGLE_VAR", [c["identity_string"]])
  def fme_eliminate_variable(constraints, var):
    pos, neg, zero = [], [], []
    for (coeffs, rhs) in constraints:
        c = coeffs.get(var, Fraction(0))
        if c > 0: pos.append((coeffs, rhs))
        elif c < 0: neg.append((coeffs, rhs))
        else: zero.append((coeffs, rhs))
    combined = list(zero)
    for pc, pr in pos:
        a = pc[var]
        for nc, nr in neg:
            b = -nc[var]
            new_coeffs = {}
            all_vars = set(pc.keys()) | set(nc.keys())
            for v in all_vars:
                if v == var: continue
                val = b * pc.get(v, Fraction(0)) + a * nc.get(v, Fraction(0))
                if val != 0: new_coeffs[v] = val
            combined.append((new_coeffs, b * pr + a * nr))
    return combined

def is_system_unsat(constraints):
    system = list(constraints)
    all_vars = set()
    for (coeffs, _) in system: all_vars.update(coeffs.keys())
    for var in sorted(all_vars):
        system = fme_eliminate_variable(system, var)
        for (coeffs, rhs) in system:
            active = {v: c for v, c in coeffs.items() if c != 0}
            if not active and rhs > 0:
                return True
    for (coeffs, rhs) in system:
        active = {v: c for v, c in coeffs.items() if c != 0}
        if not active and rhs > 0:
            return True
    return False

def is_implied_by(candidate, others):
    (c_coeffs, c_rhs) = candidate
    neg_coeffs = {v: -cv for v, cv in c_coeffs.items()}
    neg_rhs = -c_rhs + Fraction(1)
    return is_system_unsat(list(others) + [(neg_coeffs, neg_rhs)])

def canonical_form_string(lc):
    terms = []
    for v in sorted(lc.norm_coeffs.keys()):
        c = lc.norm_coeffs[v]
        if c == 0: continue
        if c == 1: terms.append(v)
        elif c == -1: terms.append(f"-{v}")
        else: terms.append(f"{int(c)}*{v}" if c == int(c) else f"{c}*{v}")
    lhs = " + ".join(terms).replace("+ -", "- ") if terms else "0"
    rhs = lc.norm_rhs
    rhs_disp = int(rhs) if rhs == int(rhs) else rhs
    return f"{lhs} >= {rhs_disp}"

def _find_conflict_core(constraints):
    n = len(constraints)
    for size in range(2, n+1):
        for subset in combinations(range(n), size):
            sub = [constraints[i] for i in subset]
            sub_tuples = [(lc.norm_coeffs, lc.norm_rhs) for lc in sub]
            if is_system_unsat(sub_tuples):
                ids = [lc.identity_string for lc in sub]
                return [{"constraint_identities": sorted(ids),
                         "reason": f"Unsatisfiable linear system (size {size})."}]
    return [{"constraint_identities": [lc.identity_string for lc in constraints],
             "reason": "System is unsatisfiable."}]

def _find_dominator(lc, others):
    for other in others:
        if is_implied_by((lc.norm_coeffs, lc.norm_rhs),
                         [(other.norm_coeffs, other.norm_rhs)]):
            return other.identity_string
    return "combination of: " + ", ".join(sorted(o.identity_string for o in others))

def _build_equivalence_groups(constraints):
    groups = defaultdict(list)
    for lc in constraints: groups[lc.canonical_key()].append(lc)
    result = []
    gid = 0
    for key, members in sorted(groups.items(), key=lambda x: str(x[0])):
        if len(members) > 1:
            ids = sorted(m.identity_string for m in members)
            result.append({"group_id": gid, "member_identities": ids,
                           "representative_identity": ids[0]})
            gid += 1
    return result

def _build_execution_result(active, unprocessable):
    per = {}
    for lc in active:
        per[lc.identity_string] = {"status": "ACTIVE", "classification": lc.classification}
    for c in unprocessable:
        per[c["identity_string"]] = {"status": "UNPROCESSED",
                                     "classification": c.get("type", "OUT_OF_SCOPE")}
    return {"bindings": {}, "per_constraint": per, "aggregate": True}

def phase3(phase2_output):
    try: parse_phase2_output(phase2_output)
    except ValueError as e:
        return {"status": "REJECTED", "reason": str(e),
                "canonical_constraints": [], "equivalence_groups": [],
                "dominance_removed": [], "execution_result": None}

    raw = phase2_output["reduced_constraints"]
    linear_constraints, unprocessable = [], []

    for c in raw:
        istr = c["identity_string"]
        ctype = c.get("type")
        if ctype == "OUT_OF_SCOPE" and "coeffs" in c and "op" in c and "value" in c:
            try:
                fcoeffs = {v: Fraction(int(cv)) for v, cv in c["coeffs"].items()}
                frhs = Fraction(int(c["value"]))
                cls = "LINEAR_MULTI_VAR" if sum(1 for cv in fcoeffs.values() if cv != 0) > 1 else "LINEAR_SINGLE_VAR"
                lc = LinearConstraint(istr, fcoeffs, c["op"], frhs, cls, [istr])
                linear_constraints.append(lc)
            except Exception:
                unprocessable.append({"identity_string": istr, "type": "OUT_OF_SCOPE",
                                      "reason": "Phase 3 extended parse error."})
        elif ctype == "OUT_OF_SCOPE":
            unprocessable.append(c)
        elif "var" in c and "op" in c and "value" in c:
            try: linear_constraints.append(build_linear_constraint_from_phase2(c))
            except Exception: unprocessable.append({"identity_string": istr, "type": "OUT_OF_SCOPE",
                                                    "reason": "Phase 3 parse error."})
        else:
            unprocessable.append({"identity_string": istr, "type": "OUT_OF_SCOPE",
                                  "reason": "Unrecognized constraint structure."})

    system_tuples = [(lc.norm_coeffs, lc.norm_rhs) for lc in linear_constraints]
    if system_tuples and is_system_unsat(system_tuples):
        conflicts = _find_conflict_core(linear_constraints)
        return {"status": "CONFLICT", "conflicts": conflicts, "execution_result": None}

    linear_constraints.sort(key=lambda lc: lc.identity_string)
    dominated, active = [], list(linear_constraints)
    changed = True
    while changed:
        changed = False
        new_active = []
        for i, lc in enumerate(active):
            others = [x for j, x in enumerate(active) if j != i]
            others_tuples = [(x.norm_coeffs, x.norm_rhs) for x in others]
            if others_tuples and is_implied_by((lc.norm_coeffs, lc.norm_rhs), others_tuples):
                dominator = _find_dominator(lc, others)
                dominated.append({"weaker_identity": lc.identity_string,
                                  "stronger_identity": dominator,
                                  "reason": f"Redundant: implied by others."})
                changed = True
            else:
                new_active.append(lc)
        active = new_active

    eq_groups = _build_equivalence_groups(active)

    canonical = []
    for lc in active:
        canonical.append({"identity_string": lc.identity_string,
                          "canonical_form": canonical_form_string(lc),
                          "classification": lc.classification,
                          "derived_from": sorted(set(lc.derived_from)),
                          "reason": lc.reason})
    dominated_ids = {d["weaker_identity"] for d in dominated}
    for lc in linear_constraints:
        if lc.identity_string in dominated_ids:
            canonical.append({"identity_string": lc.identity_string,
                              "canonical_form": canonical_form_string(lc),
                              "classification": lc.classification,
                              "derived_from": sorted(set(lc.derived_from)),
                              "reason": "Redundant: removed from active set."})
    for c in unprocessable:
        canonical.append(classify_out_of_scope(c))

    input_identities = {c["identity_string"] for c in raw}
    output_identities = {c["identity_string"] for c in canonical}
    missing = input_identities - output_identities
    for ident in missing:
        canonical.append({
            "identity_string": ident,
            "canonical_form": ident,
            "classification": "OUT_OF_SCOPE",
            "derived_from": [ident],
            "reason": "Identity ledger fallback: no processed result produced."
        })

    canonical.sort(key=lambda x: x["identity_string"])

    exec_res = _build_execution_result(active, unprocessable)

    return {"status": "OK", "canonical_constraints": canonical,
            "equivalence_groups": eq_groups, "dominance_removed": dominated,
            "execution_result": exec_res}
  PASS = FAIL = 0
def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✓  {label}"); PASS += 1
    else:
        print(f"  ✗  FAIL: {label}")
        if detail: print(f"       {detail}")
        FAIL += 1

def all_identities_present(result, expected_ids):
    if result.get("status") == "CONFLICT":
        reported = set()
        for c in result.get("conflicts", []): reported.update(c["constraint_identities"])
        return all(i in reported for i in expected_ids)
    present = {c["identity_string"] for c in result.get("canonical_constraints", [])}
    return all(i in present for i in expected_ids)

print("\n=== TEST VECTOR 1: Single-variable pass-through ===")
tv1 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["var","x"],["int",5]]',"var":"x","op":">","value":5}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r1 = phase3(tv1)
check("TV1: status OK", r1["status"]=="OK")
check("TV1: identity preserved",
      r1["canonical_constraints"][0]["identity_string"]=='[">",["var","x"],["int",5]]')
check("TV1: classification LINEAR_SINGLE_VAR",
      r1["canonical_constraints"][0]["classification"]=="LINEAR_SINGLE_VAR")
check("TV1: canonical form x >= 6",
      r1["canonical_constraints"][0]["canonical_form"]=="x >= 6")

print("\n=== TEST VECTOR 2: Multi-variable redundancy elimination ===")
tv2 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["+",["var","x"],["var","y"]],["int",10]]',
     "type":"OUT_OF_SCOPE","reason":"multi-variable",
     "coeffs":{"x":1,"y":1},"op":">","value":10},
    {"identity_string":'[">",["var","x"],["int",6]]',"var":"x","op":">","value":6},
    {"identity_string":'[">",["var","y"],["int",4]]',"var":"y","op":">","value":4}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r2 = phase3(tv2)
check("TV2: status OK", r2["status"]=="OK")
check("TV2: all 3 identities present",
      all_identities_present(r2, ['[">",["+",["var","x"],["var","y"]],["int",10]]',
                                   '[">",["var","x"],["int",6]]',
                                   '[">",["var","y"],["int",4]]']))
dom_weak = [d["weaker_identity"] for d in r2.get("dominance_removed",[])]
check("TV2: x+y>10 removed as redundant",
      '[">",["+",["var","x"],["var","y"]],["int",10]]' in dom_weak)
active_ids = [c["identity_string"] for c in r2.get("canonical_constraints",[])
              if c.get("classification") in ("LINEAR_SINGLE_VAR","LINEAR_MULTI_VAR")
              and "Redundant" not in c.get("reason","")]
check("TV2: only x>6 and y>4 remain active",
      set(active_ids)=={'[">",["var","x"],["int",6]]','[">",["var","y"],["int",4]]'})

print("\n=== TEST VECTOR 3: Multi-variable conflict ===")
tv3 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["+",["var","x"],["var","y"]],["int",10]]',
     "type":"OUT_OF_SCOPE","coeffs":{"x":1,"y":1},"op":">","value":10},
    {"identity_string":'["<",["+",["var","x"],["var","y"]],["int",5]]',
     "type":"OUT_OF_SCOPE","coeffs":{"x":1,"y":1},"op":"<","value":5}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r3 = phase3(tv3)
check("TV3: CONFLICT", r3["status"]=="CONFLICT")
check("TV3: execution_result null", r3["execution_result"] is None)
all_cf_ids = set()
for cf in r3.get("conflicts",[]): all_cf_ids.update(cf["constraint_identities"])
check("TV3: both identities in conflict",
      '[">",["+",["var","x"],["var","y"]],["int",10]]' in all_cf_ids and
      '["<",["+",["var","x"],["var","y"]],["int",5]]' in all_cf_ids)

print("\n=== TEST VECTOR 4: Nonlinear preservation ===")
tv4 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["*",["var","x"],["var","y"]],["int",10]]',
     "type":"OUT_OF_SCOPE","reason":"nonlinear"}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r4 = phase3(tv4)
check("TV4: status OK", r4["status"]=="OK")
check("TV4: identity preserved",
      r4["canonical_constraints"][0]["identity_string"]=='[">",["*",["var","x"],["var","y"]],["int",10]]')
check("TV4: classification NONLINEAR",
      r4["canonical_constraints"][0]["classification"]=="NONLINEAR")

print("\n=== TEST VECTOR 5: Determinism ===")
tv5 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["+",["var","x"],["var","y"]],["int",10]]',
     "type":"OUT_OF_SCOPE","coeffs":{"x":1,"y":1},"op":">","value":10},
    {"identity_string":'[">",["var","x"],["int",6]]',"var":"x","op":">","value":6},
    {"identity_string":'[">",["var","y"],["int",4]]',"var":"y","op":">","value":4}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r5a = json.dumps(phase3(copy.deepcopy(tv5)), sort_keys=True, default=str)
r5b = json.dumps(phase3(copy.deepcopy(tv5)), sort_keys=True, default=str)
check("TV5: deterministic output", r5a == r5b)

print("\n=== TEST VECTOR 6: Identity ledger completeness ===")
tv6 = {"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["var","a"],["int",1]]',"var":"a","op":">","value":1},
    {"identity_string":'["<",["var","b"],["int",100]]',"var":"b","op":"<","value":100},
    {"identity_string":'[">",["*",["var","a"],["var","b"]],["int",0]]',
     "type":"OUT_OF_SCOPE","reason":"nonlinear"},
    {"identity_string":'[">=",["+",["var","a"],["var","b"]],["int",50]]',
     "type":"OUT_OF_SCOPE","coeffs":{"a":1,"b":1},"op":">=","value":50}],
       "equivalence_groups":[],"dominance_removed":[],"execution_result":{}}
r6 = phase3(tv6)
in_ids = [c["identity_string"] for c in tv6["reduced_constraints"]]
out_ids = [c["identity_string"] for c in r6.get("canonical_constraints",[])]
check("TV6: all input identities present", all(i in out_ids for i in in_ids))
check("TV6: no extra identities invented", set(out_ids)==set(in_ids))

print("\n=== EDGE CASE A: Reject non-OK status ===")
ec_a = phase3({"status":"CONFLICT","reduced_constraints":[]})
check("ECA: REJECTED", ec_a["status"]=="REJECTED")

print("\n=== EDGE CASE B: Single-variable conflict (x>10, x<5) ===")
ec_b = phase3({"status":"OK","reduced_constraints":[
    {"identity_string":'[">",["var","x"],["int",10]]',"var":"x","op":">","value":10},
    {"identity_string":'["<",["var","x"],["int",5]]',"var":"x","op":"<","value":5}],
               "equivalence_groups":[],"dominance_removed":[],"execution_result":{}})
check("ECB: CONFLICT", ec_b["status"]=="CONFLICT")

print("\n=== EDGE CASE C: Multi-var, no redundancy (2x+3y>=20, x>=5, y>=2) ===")
ec_c = phase3({"status":"OK","reduced_constraints":[
    {"identity_string":'[">=",["+",["*",["int",2],["var","x"]],["*",["int",3],["var","y"]]],["int",20]]',
     "type":"OUT_OF_SCOPE","coeffs":{"x":2,"y":3},"op":">=","value":20},
    {"identity_string":'[">=",["var","x"],["int",5]]',"var":"x","op":">=","value":5},
    {"identity_string":'[">=",["var","y"],["int",2]]',"var":"y","op":">=","value":2}],
               "equivalence_groups":[],"dominance_removed":[],"execution_result":{}})
check("ECC: status OK", ec_c["status"]=="OK")
active_ids_c = [c["identity_string"] for c in ec_c.get("canonical_constraints",[])
                if "Redundant" not in c.get("reason","")]
check("ECC: 2x+3y>=20 NOT removed",
      '[">=",["+",["*",["int",2],["var","x"]],["*",["int",3],["var","y"]]],["int",20]]' in active_ids_c)

print(f"\n{'='*50}")
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} checks")
if FAIL == 0:
    print("ALL TESTS PASSED ✓")
else:
    print("SOME TESTS FAILED ✗")
    sys.exit(1)
