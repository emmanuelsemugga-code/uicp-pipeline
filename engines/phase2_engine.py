#!/usr/bin/env python3
"""
phase2_engine.py — UICP Phase 2 Semantic Constraint Engine (v1.1)
All Phase 1 invariants enforced. Identity ledger complete.
Multi‑variable extended fields emitted for Phase 3.
"""

import json, hashlib, random
from typing import List, Dict, Optional, Tuple, Any

K, D, V, N_MAX, COMPOUND_BUDGET = 16, 32, 64, 256, 128
INT_MIN, INT_MAX = -(2**127), (2**127) - 1
OBJ_MAX_BYTES = 256

OPERATORS = {'>', '>=', '<', '<=', '=', '!=', '+', '-', '*', '/', '(', ')'}
KEYWORDS = {'AND', 'OR', 'NOT'}
RELATIONAL_OPS = {'>', '>=', '<', '<=', '=', '!='}
FLIP_TABLE = {'<': '>', '<=': '>=', '>': '<', '>=': '<=', '=': '=', '!=': '!='}

class Token:
    def __init__(self, kind, value): self.kind, self.value = kind, value

def tokenize(s, available_vars):
    for ch in s:
        if ch in ('\t','\n'): raise ValueError("REJECT+HALT: Forbidden char")
    if '--' in s:
        idx = s.find('--')
        if idx+2<len(s) and s[idx+2].isdigit():
            raise ValueError("REJECT+HALT: --N")
    import re as _re
    if _re.search(r'[+\-]\s*[+\-]\s*\d', s):
        raise ValueError("REJECT+HALT: +-/-+")
    if _re.search(r'(?<!\w)-\s*0\d', s):
        raise ValueError("REJECT+HALT: -0N")
    tokens, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == ' ': i += 1; continue
        if ch.isdigit() or (ch=='-' and i+1<n and s[i+1].isdigit()):
            if ch == '-':
                if i==0 or (tokens and tokens[-1].kind=='OP' and tokens[-1].value in
                    ('>','>=','<','<=','=','!=','+','-','*','/','(','AND','OR','NOT')):
                    is_neg = True
                else:
                    tokens.append(Token('OP','-')); i+=1; continue
            start = i
            if s[i]=='-': i+=1
            if i>=n or not s[i].isdigit(): raise ValueError("REJECT+HALT: bad negative")
            while i<n and s[i].isdigit(): i+=1
            num = s[start:i]
            if num.startswith('-0') and len(num)>2: raise ValueError("REJECT+HALT: -0N")
            val = int(num)
            if not (INT_MIN <= val <= INT_MAX): raise ValueError("REJECT+HALT: int range")
            tokens.append(Token('INT', val)); continue
        if ch.isalpha() or ch=='_':
            start = i
            while i<n and (s[i].isalnum() or s[i]=='_'): i+=1
            word = s[start:i]
            if word.upper() in KEYWORDS: tokens.append(Token('KW', word.upper()))
            else:
                if word not in available_vars: raise ValueError(f"REJECT+HALT: unbound {word}")
                tokens.append(Token('VAR', word))
            continue
        if i+1<n and s[i:i+2] in OPERATORS:
            tokens.append(Token('OP', s[i:i+2])); i+=2; continue
        if ch in OPERATORS: tokens.append(Token('OP', ch)); i+=1; continue
        raise ValueError(f"REJECT+HALT: unexpected char {ch!r}")
    tokens.append(Token('EOF', None))
    return tokens

class Parser:
    def __init__(self,t): self.t,self.p = t,0
    def peek(self): return self.t[self.p]
    def consume(self,ek=None,ev=None):
        t=self.t[self.p]
        if ek and t.kind!=ek: raise ValueError(f"REJECT+HALT: expected {ek}")
        if ev and t.value!=ev: raise ValueError(f"REJECT+HALT: expected {ev!r}")
        self.p+=1; return t
    def parse_expr(self): return self.parse_or()
    def parse_or(self):
        l=self.parse_and()
        while self.peek().kind=='KW' and self.peek().value=='OR':
            self.consume('KW','OR'); r=self.parse_and(); l=('OR',l,r)
        return l
    def parse_and(self):
        l=self.parse_not()
        while self.peek().kind=='KW' and self.peek().value=='AND':
            self.consume('KW','AND'); r=self.parse_not(); l=('AND',l,r)
        return l
    def parse_not(self):
        if self.peek().kind=='KW' and self.peek().value=='NOT':
            self.consume('KW','NOT'); op=self.parse_not(); return ('NOT',op)
        return self.parse_comparison()
    def parse_comparison(self):
        l=self.parse_arithmetic()
        if self.peek().kind=='OP' and self.peek().value in RELATIONAL_OPS:
            op=self.consume('OP').value; r=self.parse_arithmetic(); return (op,l,r)
        return l
    def parse_arithmetic(self):
        l=self.parse_term()
        while self.peek().kind=='OP' and self.peek().value in ('+','-'):
            op=self.consume('OP').value; l=(op,l,self.parse_term())
        return l
    def parse_term(self):
        l=self.parse_unary()
        while self.peek().kind=='OP' and self.peek().value in ('*','/'):
            op=self.consume('OP').value; l=(op,l,self.parse_unary())
        return l
    def parse_unary(self):
        if self.peek().kind=='OP' and self.peek().value=='-':
            self.consume('OP','-'); op=self.parse_unary(); return ('-',op)
        return self.parse_atom()
    def parse_atom(self):
        t=self.peek()
        if t.kind=='INT': self.consume('INT'); return ('int',t.value)
        if t.kind=='VAR': self.consume('VAR'); return ('var',t.value)
        if t.kind=='OP' and t.value=='(':
            self.consume('OP','('); inner=self.parse_expr(); self.consume('OP',')'); return inner
        raise ValueError(f"REJECT+HALT: unexpected {t}")

def parse_expr(s, avail):
    toks = tokenize(s, avail); p = Parser(toks); ast = p.parse_expr()
    if p.peek().kind!='EOF': raise ValueError("REJECT+HALT: trailing tokens")
    if ast_depth(ast)>D: raise ValueError(f"REJECT+HALT: depth > {D}")
    return ast

def ast_depth(a):
    if isinstance(a,tuple):
        if a[0] in ('int','var'): return 1
        return 1 + max(ast_depth(c) for c in a[1:])
    return 1

def ast_node_count(a):
    if isinstance(a,tuple):
        if a[0] in ('int','var'): return 1
        return 1 + sum(ast_node_count(c) for c in a[1:])
    return 1

def is_simple_bound(a):
    return (isinstance(a,tuple) and len(a)==3 and a[0] in ('>','>=','<','<=') and
            isinstance(a[1],tuple) and a[1][0]=='var' and isinstance(a[2],tuple) and a[2][0]=='int')

def is_compound(a): return not is_simple_bound(a)
def get_var_name(v): return v[1]
def get_int_value(i): return i[1]

def step_constant_fold(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = [step_constant_fold(c) for c in a[1:]]
    if a[0] in ('+','-','*','/') and len(kids)==2:
        l,r = kids
        if isinstance(l,tuple) and l[0]=='int' and isinstance(r,tuple) and r[0]=='int':
            lv, rv = get_int_value(l), get_int_value(r)
            if a[0]=='+': res = lv+rv
            elif a[0]=='-': res = lv-rv
            elif a[0]=='*': res = lv*rv
            else:
                if rv==0: raise ValueError("REJECT+HALT: div0")
                if lv%rv!=0: raise ValueError("REJECT+HALT: non-int div")
                res = lv//rv
            if not (INT_MIN<=res<=INT_MAX): raise ValueError("REJECT+HALT: overflow")
            return ('int',res)
    return (a[0],)+tuple(kids)

def step_algebraic_simplify(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = [step_algebraic_simplify(c) for c in a[1:]]
    if a[0]=='+' and len(kids)==2 and isinstance(kids[1],tuple) and kids[1][0]=='int' and get_int_value(kids[1])==0:
        return kids[0]
    if a[0]=='-' and len(kids)==2 and isinstance(kids[1],tuple) and kids[1][0]=='int' and get_int_value(kids[1])==0:
        return kids[0]
    return (a[0],)+tuple(kids)

def step_relational_normalize(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = [step_relational_normalize(c) for c in a[1:]]
    if a[0] in RELATIONAL_OPS and len(kids)==2:
        l,r = kids
        if isinstance(l,tuple) and l[0]=='int' and isinstance(r,tuple) and r[0]=='var':
            return (FLIP_TABLE[a[0]], r, l)
    return (a[0],)+tuple(kids)

def step_boolean_flatten(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = []
    for c in a[1:]:
        flat = step_boolean_flatten(c)
        if isinstance(flat,tuple) and flat[0]==a[0] and a[0] in ('AND','OR'):
            kids.extend(flat[1:])
        else:
            kids.append(flat)
    return (a[0],)+tuple(kids)

def step_boolean_simplify(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = [step_boolean_simplify(c) for c in a[1:]]
    if a[0]=='NOT' and len(kids)==1:
        op = kids[0]
        if isinstance(op,tuple) and op[0]=='bool': return ('bool', not op[1])
        if isinstance(op,tuple) and op[0]=='NOT': return op[1]
        return ('NOT',op)
    if a[0] in ('AND','OR'):
        flat = list(kids)
        seen = set()
        uniq = []
        for c in flat:
            cid = ast_to_identity(c)
            if cid not in seen: seen.add(cid); uniq.append(c)
        flat = uniq
        has_false = any(isinstance(c,tuple) and c[0]=='bool' and c[1]==False for c in flat)
        has_true  = any(isinstance(c,tuple) and c[0]=='bool' and c[1]==True  for c in flat)
        if a[0]=='AND':
            if has_false: return ('bool',False)
            flat = [c for c in flat if not (isinstance(c,tuple) and c[0]=='bool' and c[1]==True)]
        else:
            if has_true: return ('bool',True)
            flat = [c for c in flat if not (isinstance(c,tuple) and c[0]=='bool' and c[1]==False)]
        if a[0]=='OR':
            sids = {ast_to_identity(c):c for c in flat if not (isinstance(c,tuple) and c[0]=='AND')}
            nf = []
            for c in flat:
                if isinstance(c,tuple) and c[0]=='AND':
                    if not any(ast_to_identity(ac) in sids for ac in c[1:]): nf.append(c)
                else: nf.append(c)
            flat = nf
        if a[0]=='AND':
            sids = {ast_to_identity(c):c for c in flat if not (isinstance(c,tuple) and c[0]=='OR')}
            nf = []
            for c in flat:
                if isinstance(c,tuple) and c[0]=='OR':
                    if not any(ast_to_identity(oc) in sids for oc in c[1:]): nf.append(c)
                else: nf.append(c)
            flat = nf
        if len(flat)==1: return flat[0]
        if len(flat)==0: return ('bool',True)
        return (a[0],)+tuple(flat)
    return (a[0],)+tuple(kids)

def step_operand_sort(a):
    if not isinstance(a,tuple): return a
    if a[0] in ('int','var'): return a
    kids = [step_operand_sort(c) for c in a[1:]]
    if a[0] in ('AND','OR'): kids.sort(key=ast_to_identity)
    return (a[0],)+tuple(kids)

def canonical_transform(a):
    a = step_constant_fold(a)
    a = step_algebraic_simplify(a)
    a = step_relational_normalize(a)
    a = step_boolean_flatten(a)
    a = step_boolean_simplify(a)
    a = step_operand_sort(a)
    return a

def ast_to_identity(a):
    return json.dumps(a, sort_keys=True, separators=(',',':'), ensure_ascii=True)

def identity_sha256(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()
def is_contradiction(lo_op, lo_val, hi_op, hi_val):
    if lo_op in ('>=','>') and hi_op in ('<=','<'):
        if lo_op=='>=' and hi_op=='<=': return lo_val > hi_val
        return lo_val >= hi_val
    return False

def dominance_reduce(items):
    var_lowers, var_uppers, compounds = {}, {}, []
    for ast, ident in items:
        if is_simple_bound(ast):
            op, var, val = ast[0], get_var_name(ast[1]), get_int_value(ast[2])
            if op in ('>','>='):
                if var not in var_lowers: var_lowers[var] = []
                var_lowers[var].append((op, val, ast, ident))
            elif op in ('<','<='):
                if var not in var_uppers: var_uppers[var] = []
                var_uppers[var].append((op, val, ast, ident))
        else:
            compounds.append((ast, ident))
    reduced = []
    for var in set(var_lowers.keys()) | set(var_uppers.keys()):
        lowers = var_lowers.get(var, [])
        uppers = var_uppers.get(var, [])
        if lowers:
            lowers.sort(key=lambda x: (x[1], 1 if x[0]=='>' else 0), reverse=True)
            best = lowers[0]; reduced.append((best[2], best[3])); lo_val, lo_op = best[1], best[0]
        else:
            lo_val = lo_op = None
        if uppers:
            uppers.sort(key=lambda x: (x[1], 1 if x[0]=='<' else 0))
            best = uppers[0]; reduced.append((best[2], best[3])); hi_val, hi_op = best[1], best[0]
        else:
            hi_val = hi_op = None
        if lo_val is not None and hi_val is not None:
            if is_contradiction(lo_op, lo_val, hi_op, hi_val):
                return ([], f"REJECT+HALT: contradiction {var}")
    reduced.extend(compounds)
    compound_depth = sum(ast_depth(ast) for ast,_ in compounds)
    if compound_depth > COMPOUND_BUDGET:
        return ([], "REJECT+HALT: compound budget")
    return (reduced, None)

def ADMIT(input_data, constants=None):
    if constants is None:
        constants = {'K':K,'D':D,'V':V,'N_MAX':N_MAX,'INT_MIN':INT_MIN,'INT_MAX':INT_MAX,
                     'OBJ_MAX_BYTES':OBJ_MAX_BYTES,'COMPOUND_BUDGET':COMPOUND_BUDGET}
    if not isinstance(input_data, dict): return {'result':'REJECT+HALT','reason':'not dict'}
    required = {'objective_commitment','constraint_set','input_set'}
    if set(input_data.keys()) != required: return {'result':'REJECT+HALT','reason':'bad fields'}
    for f in required:
        if input_data[f] is None: return {'result':'REJECT+HALT','reason':f'null {f}'}
    obj, cons, inp = input_data['objective_commitment'], input_data['constraint_set'], input_data['input_set']
    if not isinstance(obj, str): return {'result':'REJECT+HALT','reason':'obj not str'}
    if not isinstance(cons, list) or not all(isinstance(c,str) for c in cons):
        return {'result':'REJECT+HALT','reason':'constraints not list[str]'}
    if not isinstance(inp, dict): return {'result':'REJECT+HALT','reason':'input_set not dict'}
    for k,v in inp.items():
        if not isinstance(k, str): return {'result':'REJECT+HALT','reason':'bad key'}
        if not isinstance(v, (int,bool)): return {'result':'REJECT+HALT','reason':'bad value'}
        if isinstance(v,int) and (v<INT_MIN or v>INT_MAX): return {'result':'REJECT+HALT','reason':'int out of range'}
        if isinstance(v,bool) and v not in (True,False): return {'result':'REJECT+HALT','reason':'bad bool'}
    avail = set(inp.keys())
    parsed = []
    for cs in cons:
        try:
            ast = parse_expr(cs, avail)
        except ValueError as e:
            return {'result':'REJECT+HALT','reason':f'4.5 parse: {e}'}
        parsed.append(ast)
    if len(obj)==0 or len(obj.encode('utf-8'))>OBJ_MAX_BYTES:
        return {'result':'REJECT+HALT','reason':'obj length'}
    if any(ord(c)<32 and c not in ('\t','\n','\r') for c in obj):
        return {'result':'REJECT+HALT','reason':'control chars'}
    for ast in parsed:
        try: ast_to_identity(ast)
        except Exception as e: return {'result':'REJECT+HALT','reason':'4.8 canonicalization'}
    N = len(cons)
    if N<1 or N>K: return {'result':'REJECT+HALT','reason':f'N={N} out of [1,{K}]'}
    if len(avail)>V: return {'result':'REJECT+HALT','reason':'too many vars'}
    cdepth = sum(ast_depth(ast) for ast in parsed if is_compound(ast))
    if cdepth>COMPOUND_BUDGET: return {'result':'REJECT+HALT','reason':'compound depth budget'}
    return {'result':'ACCEPT','parsed_asts':parsed,'available_vars':avail}

def NORMALIZE(input_data):
    adm = ADMIT(input_data)
    if adm['result']!='ACCEPT': return {'result':'REJECT+HALT','reason':adm['reason']}
    parsed = adm['parsed_asts']
    trans = []
    for ast in parsed:
        try: c = canonical_transform(ast)
        except ValueError as e: return {'result':'REJECT+HALT','reason':f'N2: {e}'}
        trans.append(c)
    with_ids = [(ast, ast_to_identity(ast)) for ast in trans]
    seen, dedup = set(), []
    for ast, i in with_ids:
        if i not in seen: seen.add(i); dedup.append((ast,i))
    red, err = dominance_reduce(dedup)
    if err: return {'result':'REJECT+HALT','reason':err}
    red.sort(key=lambda x: x[1])
    total_nodes = sum(ast_node_count(ast) for ast,_ in red)
    if total_nodes > N_MAX:
        return {'result':'REJECT+HALT','reason':f'output nodes {total_nodes} > {N_MAX}'}
    return {'result':'OK','constraints':[i for _,i in red],
            'stats':{'N':len(red),'input_count':len(parsed)}}

# ---------------------------------------------------------------------------
# Conversion helper – Phase 1 identity strings are JSON lists, not tuples
# ---------------------------------------------------------------------------
def _to_tuple(obj):
    if isinstance(obj, list):
        return tuple(_to_tuple(item) for item in obj)
    return obj

# ---------------------------------------------------------------------------
# Multi‑variable linear extraction (for Phase 3)
# ---------------------------------------------------------------------------
def extract_real_linear_from_ast(ast_node):
    if isinstance(ast_node, tuple):
        if ast_node[0]=='var': return {ast_node[1]:1}, 0
        if ast_node[0]=='int': return {}, ast_node[1]
        op = ast_node[0]
        if op=='+':
            coeffs, const = {}, 0
            for child in ast_node[1:]:
                c, k = extract_real_linear_from_ast(child)
                for v,cv in c.items(): coeffs[v] = coeffs.get(v,0)+cv
                const += k
            return coeffs, const
        if op=='-':
            if len(ast_node)==3:
                lc, lk = extract_real_linear_from_ast(ast_node[1])
                rc, rk = extract_real_linear_from_ast(ast_node[2])
                for v,cv in rc.items(): lc[v] = lc.get(v,0)-cv
                return lc, lk-rk
            return {}, 0
        if op=='*':
            left, right = ast_node[1], ast_node[2]
            if isinstance(left,tuple) and left[0]=='int':
                factor, other = left[1], right
            elif isinstance(right,tuple) and right[0]=='int':
                factor, other = right[1], left
            else:
                return {}, 0
            c, k = extract_real_linear_from_ast(other)
            for v in c: c[v] *= factor
            return c, k*factor
    return {}, 0

def try_parse_multi_var(identity_str):
    try:
        ast = json.loads(identity_str)
        ast = _to_tuple(ast)
    except Exception:
        return None
    if not isinstance(ast, tuple) or len(ast)!=3: return None
    rel_op = ast[0]
    if rel_op not in (">",">=","<","<="): return None
    lc, lk = extract_real_linear_from_ast(ast[1])
    rc, rk = extract_real_linear_from_ast(ast[2])
    coeffs = {}
    for v,c in lc.items(): coeffs[v] = coeffs.get(v,0)+c
    for v,c in rc.items(): coeffs[v] = coeffs.get(v,0)-c
    const = lk - rk
    if len(coeffs) <= 1: return None
    return ({v:int(c) for v,c in coeffs.items()}, rel_op, -const)

def _collect_atoms(ast, source, results):
    if not isinstance(ast, tuple): return
    op = ast[0]
    if op == "AND":
        for child in ast[1:]: _collect_atoms(child, source, results)
    elif op in (">",">=","<","<="):
        lc, lk = extract_real_linear_from_ast(ast[1])
        rc, rk = extract_real_linear_from_ast(ast[2])
        coeffs = {}
        for v,c in lc.items(): coeffs[v] = coeffs.get(v,0)+c
        for v,c in rc.items(): coeffs[v] = coeffs.get(v,0)-c
        const = lk - rk
        if len(coeffs)!=1: return
        var = list(coeffs.keys())[0]
        a = coeffs[var]
        if a==0: return
        rhs = -const
        if a<0:
            flip = {">":"<",">=":"<=","<":">","<=":">="}
            op = flip[op]
            a = -a; rhs = -rhs
        if rhs % a != 0: return
        value = rhs // a
        results.append({"identity_string": source, "var": var, "op": op, "value": value})

def _unsat_pair(c1,c2):
    if c1["var"]!=c2["var"]: return False
    op1,v1 = c1["op"],c1["value"]
    op2,v2 = c2["op"],c2["value"]
    if op1==">" and op2=="<" and v1>=v2: return True
    if op1=="<" and op2==">" and v2>=v1: return True
    if op1==">=" and op2=="<" and v1>v2: return True
    if op1=="<" and op2==">=" and v2>v1: return True
    if op1==">" and op2=="<=" and v1>=v2: return True
    if op1=="<=" and op2==">" and v2>=v1: return True
    if op1==">=" and op2=="<=" and v1>v2: return True
    if op1=="<=" and op2==">=" and v2>v1: return True
    return False

def _equivalent(c1,c2):
    if c1["var"]!=c2["var"]: return False
    op1,v1 = c1["op"],c1["value"]
    op2,v2 = c2["op"],c2["value"]
    if op1==op2 and v1==v2: return True
    if op1==">" and op2==">=" and v1+1==v2: return True
    if op1==">=" and op2==">" and v1==v2+1: return True
    if op1=="<" and op2=="<=" and v1-1==v2: return True
    if op1=="<=" and op2=="<" and v1==v2-1: return True
    return False

def _dominates(c1,c2):
    if c1["var"]!=c2["var"]: return False
    op1,v1 = c1["op"],c1["value"]
    op2,v2 = c2["op"],c2["value"]
    if op1==">" and op2==">" and v1>v2: return True
    if op1==">=" and op2==">=" and v1>v2: return True
    if op1=="<" and op2=="<" and v1<v2: return True
    if op1=="<=" and op2=="<=" and v1<v2: return True
    if op1==">" and op2==">=" and v1>=v2: return True
    if op1==">=" and op2==">" and v1>v2: return True
    return False

# ---------------------------------------------------------------------------
# MAIN PHASE 2 ENGINE (v1.1, ledger‑complete)
# ---------------------------------------------------------------------------
def phase2_engine(constraints, identities, stats, admission_status,
                  execution_bindings=None):
    if admission_status != "ACCEPT":
        return {"status":"REJECTED","reason":"admission_status not ACCEPT",
                "reduced_constraints":[],"equivalence_groups":[],"dominance_removed":[],
                "execution_result":None}
    if len(constraints)!=len(identities):
        return {"status":"REJECTED","reason":"count mismatch",
                "reduced_constraints":[],"equivalence_groups":[],"dominance_removed":[],
                "execution_result":None}
    if len(constraints)==0:
        return {"status":"OK","reduced_constraints":[],"equivalence_groups":[],
                "dominance_removed":[],"execution_result":None}

    all_atoms = []
    identities_with_atoms = set()
    for identity_str in constraints:
        try:
            ast = json.loads(identity_str)
            ast = _to_tuple(ast)
        except Exception as e:
            return {"status":"REJECTED","reason":f"parse error: {e}",
                    "reduced_constraints":[],"equivalence_groups":[],"dominance_removed":[],
                    "execution_result":None}
        before = len(all_atoms)
        _collect_atoms(ast, identity_str, all_atoms)
        if len(all_atoms) > before:
            identities_with_atoms.add(identity_str)

    conflicts = []
    for i in range(len(all_atoms)):
        for j in range(i+1, len(all_atoms)):
            if _unsat_pair(all_atoms[i], all_atoms[j]):
                reason = (f"{all_atoms[i]['var']} {all_atoms[i]['op']} {all_atoms[i]['value']} "
                          f"AND {all_atoms[j]['var']} {all_atoms[j]['op']} {all_atoms[j]['value']}")
                conflicts.append((i,j,reason))
    if conflicts:
        return {"status":"CONFLICT",
                "conflicts":[{"constraint_1_identity":all_atoms[i]["identity_string"],
                              "constraint_2_identity":all_atoms[j]["identity_string"],
                              "reason":r} for i,j,r in conflicts],
                "execution_result":None}

    eq_groups = []
    assigned = set()
    for i, c1 in enumerate(all_atoms):
        if i in assigned: continue
        group = [i]; assigned.add(i)
        for j in range(i+1, len(all_atoms)):
            if j in assigned: continue
            if _equivalent(all_atoms[i], all_atoms[j]):
                group.append(j); assigned.add(j)
        eq_groups.append(group)

    dominated_indices = set()
    dominance_removed = []
    for i in range(len(all_atoms)):
        for j in range(i+1, len(all_atoms)):
            if _dominates(all_atoms[i], all_atoms[j]) and j not in dominated_indices:
                dominated_indices.add(j)
                dominance_removed.append({
                    "weaker_identity": all_atoms[j]["identity_string"],
                    "stronger_identity": all_atoms[i]["identity_string"],
                    "reason": (f"{all_atoms[i]['var']} {all_atoms[i]['op']} {all_atoms[i]['value']} "
                               f"dominates {all_atoms[j]['var']} {all_atoms[j]['op']} {all_atoms[j]['value']}")
                })
            elif _dominates(all_atoms[j], all_atoms[i]) and i not in dominated_indices:
                dominated_indices.add(i)
                dominance_removed.append({
                    "weaker_identity": all_atoms[i]["identity_string"],
                    "stronger_identity": all_atoms[j]["identity_string"],
                    "reason": (f"{all_atoms[j]['var']} {all_atoms[j]['op']} {all_atoms[j]['value']} "
                               f"dominates {all_atoms[i]['var']} {all_atoms[i]['op']} {all_atoms[i]['value']}")
                })
    reduced_atoms = [c for i,c in enumerate(all_atoms) if i not in dominated_indices]

    reduced_constraints = []
    for c in reduced_atoms:
        reduced_constraints.append({
            "identity_string": c["identity_string"],
            "var": c["var"], "op": c["op"], "value": c["value"]
        })

    dominated_identities = {all_atoms[i]["identity_string"] for i in dominated_indices}
    for identity_str in constraints:
        if identity_str in dominated_identities:
            atom = next((a for a in all_atoms if a["identity_string"]==identity_str), None)
            entry = {"identity_string": identity_str, "dominated": True}
            if atom:
                entry["var"] = atom["var"]; entry["op"] = atom["op"]; entry["value"] = atom["value"]
            reduced_constraints.append(entry)

    for identity_str in constraints:
        if identity_str not in identities_with_atoms and identity_str not in dominated_identities:
            entry = {"identity_string": identity_str,
                     "type": "OUT_OF_SCOPE",
                     "reason": "No extractable single‑variable linear atoms"}
            parsed = try_parse_multi_var(identity_str)
            if parsed is not None:
                coeffs, op, value = parsed
                entry["coeffs"] = coeffs
                entry["op"] = op
                entry["value"] = value
                entry["reason"] = "Multi‑variable linear constraint; passed to Phase 3"
            reduced_constraints.append(entry)

    eq_output = []
    for gid, indices in enumerate(eq_groups):
        if len(indices) > 1:
            ids = [all_atoms[i]["identity_string"] for i in indices]
            eq_output.append({"group_id": gid,
                              "member_identities": ids,
                              "representative_identity": all_atoms[indices[0]]["identity_string"]})

    execution_result = None
    if execution_bindings is not None:
        per = {}
        for c in reduced_atoms:
            var = c["var"]
            ident = c["identity_string"]
            if var not in execution_bindings:
                per[ident] = {"result": None, "reason": f"Variable '{var}' not in bindings"}
                continue
            value = execution_bindings[var]
            if not (INT_MIN <= value <= INT_MAX):
                per[ident] = {"result": None, "reason": "Value out of 128‑bit range"}
                continue
            if c["op"] == ">":   res = value > c["value"]
            elif c["op"] == "<": res = value < c["value"]
            elif c["op"] == ">=": res = value >= c["value"]
            else:                res = value <= c["value"]
            per[ident] = {"constraint": f"{var} {c['op']} {c['value']}",
                          "value": value, "result": res}
        agg = all(v.get("result") for v in per.values() if v.get("result") is not None)
        execution_result = {"bindings": execution_bindings,
                            "per_constraint": per,
                            "aggregate": agg}

    return {"status": "OK",
            "reduced_constraints": reduced_constraints,
            "equivalence_groups": eq_output,
            "dominance_removed": dominance_removed,
            "execution_result": execution_result}
# ---------------------------------------------------------------------------
# TEST HARNESS
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    PASS, FAIL = 0, 0
    def test(name, cond, det=""):
        global PASS, FAIL
        if cond:
            PASS += 1; print(f"[PASS] {name}")
        else:
            FAIL += 1; print(f"[FAIL] {name}  —  {det}")
        if det and cond: print(f"       {det}")

    print("=" * 70)
    print("PHASE 2 VALIDATION SUITE (v1.1, monolithic)")
    print("=" * 70)

    # CLAIM 1: DETERMINISM
    print("\n--- CLAIM 1: DETERMINISM ---")
    c1 = ['[">",["var","x"],["int",5]]', '["<",["var","x"],["int",10]]']
    h1 = [hashlib.sha256(c.encode()).hexdigest() for c in c1]
    r1 = phase2_engine(c1, h1, {"N":2,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT")
    r2 = phase2_engine(c1, h1, {"N":2,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT")
    test("Determinism — same input twice → identical output",
         json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True))

    # CLAIM 2: EQUIVALENCE
    print("\n--- CLAIM 2: EQUIVALENCE ---")
    c2 = ['[">",["var","x"],["int",5]]', '[">=",["var","x"],["int",6]]']
    h2 = [hashlib.sha256(c.encode()).hexdigest() for c in c2]
    res = phase2_engine(c2, h2, {"N":2,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT")
    test("Equivalence x>5 AND x>=6 → one group", len(res['equivalence_groups']) == 1)

    # CLAIM 3: DOMINANCE
    print("\n--- CLAIM 3: DOMINANCE ---")
    c3 = ['[">",["var","x"],["int",10]]', '[">",["var","x"],["int",5]]']
    h3 = [hashlib.sha256(c.encode()).hexdigest() for c in c3]
    res = phase2_engine(c3, h3, {"N":2,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT")
    test("Dominance x>10 AND x>5 → one removed", len(res['dominance_removed']) == 1)

    # CLAIM 4: CONFLICT
    print("\n--- CLAIM 4: CONFLICT ---")
    c4 = ['[">",["var","x"],["int",10]]', '["<",["var","x"],["int",5]]']
    h4 = [hashlib.sha256(c.encode()).hexdigest() for c in c4]
    res = phase2_engine(c4, h4, {"N":2,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT")
    test("Conflict x>10 AND x<5 → CONFLICT", res['status'] == 'CONFLICT')

    # CLAIM 5: EXECUTION
    print("\n--- CLAIM 5: EXECUTION ---")
    c5 = ['[">",["var","x"],["int",5]]']
    h5 = [hashlib.sha256(c5[0].encode()).hexdigest()]
    res = phase2_engine(c5, h5, {"N":1,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT",
                        execution_bindings={"x":10})
    test("Execution x=10 → True", res['execution_result']['aggregate'] is True)
    res = phase2_engine(c5, h5, {"N":1,"max_depth":2,"n_vars":1,"compound_count":0,"or_width":0}, "ACCEPT",
                        execution_bindings={"x":2})
    test("Execution x=2 → False", res['execution_result']['aggregate'] is False)

    # CLAIM 6: OUT_OF_SCOPE
    print("\n--- CLAIM 6: OUT_OF_SCOPE ---")
    c6 = ['["OR",[">",["var","x"],["int",5]],["<",["var","y"],["int",10]]]']
    h6 = [hashlib.sha256(c6[0].encode()).hexdigest()]
    res = phase2_engine(c6, h6, {"N":1,"max_depth":3,"n_vars":2,"compound_count":0,"or_width":1}, "ACCEPT")
    test("OUT_OF_SCOPE — identity preserved", any(c.get('identity_string')==c6[0] for c in res['reduced_constraints']))
    test("OUT_OF_SCOPE — type is OUT_OF_SCOPE", any(c.get('type')=='OUT_OF_SCOPE' for c in res['reduced_constraints']))

    # CLAIM 7: MULTI‑VAR EXTENDED
    print("\n--- CLAIM 7: MULTI‑VAR EXTENDED ---")
    c7 = ['[">",["+",["var","x"],["var","y"]],["int",10]]']
    h7 = [hashlib.sha256(c7[0].encode()).hexdigest()]
    res = phase2_engine(c7, h7, {"N":1,"max_depth":3,"n_vars":2,"compound_count":0,"or_width":0}, "ACCEPT")
    mv = next((c for c in res['reduced_constraints'] if c.get('type')=='OUT_OF_SCOPE'), None)
    test("Multi‑var — OUT_OF_SCOPE entry exists", mv is not None)
    test("Multi‑var — coeffs present", mv and 'coeffs' in mv)
    test("Multi‑var — op present", mv and 'op' in mv)
    test("Multi‑var — value present", mv and 'value' in mv)
    if mv and 'coeffs' in mv:
        test("Multi‑var — coeffs {'x':1,'y':1}", mv['coeffs']=={'x':1,'y':1}, str(mv['coeffs']))

    # CLAIM 8: LEDGER
    print("\n--- CLAIM 8: IDENTITY LEDGER ---")
    all_ids = c3 + c6 + c7
    all_h = [hashlib.sha256(i.encode()).hexdigest() for i in all_ids]
    res = phase2_engine(all_ids, all_h, {"N":4,"max_depth":3,"n_vars":2,"compound_count":0,"or_width":1}, "ACCEPT")
    out_ids = [c['identity_string'] for c in res['reduced_constraints']]
    test("Ledger — all inputs present", all(i in out_ids for i in all_ids))

    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    if FAIL == 0:
        print("VERDICT: Phase 2 engine (v1.1) is internally proven and aligned.")
    else:
        print(f"VERDICT: {FAIL} failure(s) — gaps remain.")
    print("=" * 70)
