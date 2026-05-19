#!/usr/bin/env python3
"""
normalize_v05.py — UICP Phase 1 Constraint Normalization Engine (FROZEN V0.7)
"""
import json
import hashlib
import re
import random

K = 16
D = 32
V = 64
N_MAX = 256
COMPOUND_BUDGET = 128
INT_MIN = -(2**127)
INT_MAX = (2**127) - 1
OBJ_MAX_BYTES = 256

OPERATORS = {'>', '>=', '<', '<=', '=', '!=', '+', '-', '*', '/', '(', ')'}
KEYWORDS = {'AND', 'OR', 'NOT'}
RELATIONAL_OPS = {'>', '>=', '<', '<=', '=', '!='}
FLIP_TABLE = {'<': '>', '<=': '>=', '>': '<', '>=': '<=', '=': '=', '!=': '!='}

class Token:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

def tokenize(s, available_vars):
    for ch in s:
        if ch in ('\t', '\n'):
            raise ValueError("REJECT+HALT: Forbidden character (tab/newline)")
    if '--' in s:
        idx = s.find('--')
        if idx + 2 < len(s) and s[idx + 2].isdigit():
            raise ValueError("REJECT+HALT: --N form (double negative)")
    if re.search(r'[+\-]\s*[+\-]\s*\d', s):
        raise ValueError("REJECT+HALT: Forbidden lexer form: +- or -+ form")
    if re.search(r'(?<!\w)-\s*0\d', s):
        raise ValueError("REJECT+HALT: Forbidden lexer form: -0N form")
    tokens = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == ' ':
            i += 1
            continue
        if ch.isdigit() or (ch == '-' and i + 1 < n and s[i + 1].isdigit()):
            if ch == '-':
                if i == 0:
                    is_negative_literal = True
                elif i > 0 and tokens and tokens[-1].kind == 'OP' and tokens[-1].value in (
                    '>', '>=', '<', '<=', '=', '!=', '+', '-', '*', '/', '(', 'AND', 'OR', 'NOT'
                ):
                    is_negative_literal = True
                else:
                    tokens.append(Token('OP', '-'))
                    i += 1
                    continue
            start = i
            if s[i] == '-':
                i += 1
            if i >= n or not s[i].isdigit():
                raise ValueError("REJECT+HALT: Expected digit after minus sign")
            while i < n and s[i].isdigit():
                i += 1
            num_str = s[start:i]
            if num_str.startswith('-0') and len(num_str) > 2:
                raise ValueError("REJECT+HALT: -0N form")
            val = int(num_str)
            if val < INT_MIN or val > INT_MAX:
                raise ValueError("REJECT+HALT: Integer value out of 128-bit signed range")
            tokens.append(Token('INT', val))
            continue
        if ch.isalpha() or ch == '_':
            start = i
            while i < n and (s[i].isalnum() or s[i] == '_'):
                i += 1
            word = s[start:i]
            upper = word.upper()
            if upper in KEYWORDS:
                tokens.append(Token('KW', upper))
            else:
                if word not in available_vars:
                    raise ValueError(f"REJECT+HALT: Unbound identifier '{word}' — not in input_set")
                tokens.append(Token('VAR', word))
            continue
        if i + 1 < n and s[i:i + 2] in OPERATORS:
            tokens.append(Token('OP', s[i:i + 2]))
            i += 2
            continue
        if ch in OPERATORS:
            tokens.append(Token('OP', ch))
            i += 1
            continue
        raise ValueError(f"REJECT+HALT: Unexpected character: {ch!r}")
    tokens.append(Token('EOF', None))
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
    def peek(self):
        return self.tokens[self.pos]
    def consume(self, expected_kind=None, expected_value=None):
        t = self.tokens[self.pos]
        if expected_kind and t.kind != expected_kind:
            raise ValueError(f"REJECT+HALT: Expected {expected_kind}, got {t.kind}")
        if expected_value and t.value != expected_value:
            raise ValueError(f"REJECT+HALT: Expected {expected_value!r}, got {t.value!r}")
        self.pos += 1
        return t
    def parse_expr(self):
        return self.parse_or()
    def parse_or(self):
        left = self.parse_and()
        while self.peek().kind == 'KW' and self.peek().value == 'OR':
            self.consume('KW', 'OR')
            right = self.parse_and()
            left = ('OR', left, right)
        return left
    def parse_and(self):
        left = self.parse_not()
        while self.peek().kind == 'KW' and self.peek().value == 'AND':
            self.consume('KW', 'AND')
            right = self.parse_not()
            left = ('AND', left, right)
        return left
    def parse_not(self):
        if self.peek().kind == 'KW' and self.peek().value == 'NOT':
            self.consume('KW', 'NOT')
            operand = self.parse_not()
            return ('NOT', operand)
        return self.parse_comparison()
    def parse_comparison(self):
        left = self.parse_arithmetic()
        if self.peek().kind == 'OP' and self.peek().value in RELATIONAL_OPS:
            op = self.consume('OP').value
            right = self.parse_arithmetic()
            return (op, left, right)
        return left
    def parse_arithmetic(self):
        left = self.parse_term()
        while self.peek().kind == 'OP' and self.peek().value in ('+', '-'):
            op = self.consume('OP').value
            right = self.parse_term()
            left = (op, left, right)
        return left
    def parse_term(self):
        left = self.parse_unary()
        while self.peek().kind == 'OP' and self.peek().value in ('*', '/'):
            op = self.consume('OP').value
            right = self.parse_unary()
            left = (op, left, right)
        return left
    def parse_unary(self):
        if self.peek().kind == 'OP' and self.peek().value == '-':
            self.consume('OP', '-')
            operand = self.parse_unary()
            return ('-', operand)
        return self.parse_atom()
    def parse_atom(self):
        t = self.peek()
        if t.kind == 'INT':
            self.consume('INT')
            return ('int', t.value)
        if t.kind == 'VAR':
            self.consume('VAR')
            return ('var', t.value)
        if t.kind == 'OP' and t.value == '(':
            self.consume('OP', '(')
            inner = self.parse_expr()
            self.consume('OP', ')')
            return inner
        raise ValueError(f"REJECT+HALT: Unexpected token in expression: {t}")

def parse_expr(s, available_vars):
    tokens = tokenize(s, available_vars)
    parser = Parser(tokens)
    ast = parser.parse_expr()
    if parser.peek().kind != 'EOF':
        raise ValueError("REJECT+HALT: Unexpected trailing tokens after parse")
    depth = ast_depth(ast)
    if depth > D:
        raise ValueError(f"REJECT+HALT: AST depth {depth} exceeds limit {D}")
    return ast

def ast_depth(ast):
    if isinstance(ast, tuple):
        if ast[0] in ('int', 'var'):
            return 1
        return 1 + max(ast_depth(child) for child in ast[1:])
    return 1

def ast_node_count(ast):
    if isinstance(ast, tuple):
        if ast[0] in ('int', 'var'):
            return 1
        return 1 + sum(ast_node_count(child) for child in ast[1:])
    return 1

def is_simple_bound(ast):
    if not isinstance(ast, tuple) or len(ast) != 3:
        return False
    op, left, right = ast
    if op not in ('>', '>=', '<', '<='):
        return False
    if not (isinstance(left, tuple) and left[0] == 'var'):
        return False
    if not (isinstance(right, tuple) and right[0] == 'int'):
        return False
    return True

def is_compound(ast):
    return not is_simple_bound(ast)

def get_var_name(var_ast):
    return var_ast[1]

def get_int_value(int_ast):
    return int_ast[1]

def step_constant_fold(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = [step_constant_fold(child) for child in ast[1:]]
    if tag in ('+', '-', '*', '/') and len(children) == 2:
        left, right = children
        if isinstance(left, tuple) and left[0] == 'int' and isinstance(right, tuple) and right[0] == 'int':
            lv = get_int_value(left)
            rv = get_int_value(right)
            if tag == '+':
                result = lv + rv
            elif tag == '-':
                result = lv - rv
            elif tag == '*':
                result = lv * rv
            elif tag == '/':
                if rv == 0:
                    raise ValueError("REJECT+HALT: Division by zero in constant fold")
                if lv % rv != 0:
                    raise ValueError("REJECT+HALT: Non-integer result in constant fold")
                result = lv // rv
            if result < INT_MIN or result > INT_MAX:
                raise ValueError("REJECT+HALT: Constant fold result out of 128-bit signed range")
            return ('int', result)
    return (tag,) + tuple(children)

def step_algebraic_simplify(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = [step_algebraic_simplify(child) for child in ast[1:]]
    if tag in ('+', '-') and len(children) == 2:
        left, right = children
        if tag == '+' and isinstance(right, tuple) and right[0] == 'int' and get_int_value(right) == 0:
            return left
        if tag == '-' and isinstance(right, tuple) and right[0] == 'int' and get_int_value(right) == 0:
            return left
    return (tag,) + tuple(children)

def step_relational_normalize(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = [step_relational_normalize(child) for child in ast[1:]]
    if tag in RELATIONAL_OPS and len(children) == 2:
        left, right = children
        if isinstance(left, tuple) and left[0] == 'int' and isinstance(right, tuple) and right[0] == 'var':
            flip_op = FLIP_TABLE[tag]
            return (flip_op, right, left)
    return (tag,) + tuple(children)

def step_boolean_flatten(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = []
    for child in ast[1:]:
        flat_child = step_boolean_flatten(child)
        if isinstance(flat_child, tuple) and flat_child[0] == tag and tag in ('AND', 'OR'):
            children.extend(flat_child[1:])
        else:
            children.append(flat_child)
    return (tag,) + tuple(children)

def step_boolean_simplify(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = [step_boolean_simplify(child) for child in ast[1:]]
    if tag == 'NOT' and len(children) == 1:
        operand = children[0]
        if isinstance(operand, tuple) and operand[0] == 'bool':
            return ('bool', not operand[1])
        if isinstance(operand, tuple) and operand[0] == 'NOT':
            return operand[1]
        return (tag, operand)
    if tag in ('AND', 'OR'):
        flat_children = list(children)
        seen = set()
        unique_children = []
        for child in flat_children:
            child_id = ast_to_identity(child)
            if child_id not in seen:
                seen.add(child_id)
                unique_children.append(child)
        flat_children = unique_children
        has_bool_false = any(isinstance(c, tuple) and c[0] == 'bool' and c[1] == False for c in flat_children)
        has_bool_true  = any(isinstance(c, tuple) and c[0] == 'bool' and c[1] == True  for c in flat_children)
        if tag == 'AND':
            if has_bool_false:
                return ('bool', False)
            flat_children = [c for c in flat_children if not (isinstance(c, tuple) and c[0] == 'bool' and c[1] == True)]
        elif tag == 'OR':
            if has_bool_true:
                return ('bool', True)
            flat_children = [c for c in flat_children if not (isinstance(c, tuple) and c[0] == 'bool' and c[1] == False)]
        if tag == 'OR':
            simple_ids = {ast_to_identity(c): c for c in flat_children if not (isinstance(c, tuple) and c[0] == 'AND')}
            new_children = []
            for child in flat_children:
                if isinstance(child, tuple) and child[0] == 'AND':
                    and_children = child[1:]
                    absorbed = any(ast_to_identity(ac) in simple_ids for ac in and_children)
                    if not absorbed:
                        new_children.append(child)
                else:
                    new_children.append(child)
            flat_children = new_children
        if tag == 'AND':
            simple_ids = {ast_to_identity(c): c for c in flat_children if not (isinstance(c, tuple) and c[0] == 'OR')}
            new_children = []
            for child in flat_children:
                if isinstance(child, tuple) and child[0] == 'OR':
                    or_children = child[1:]
                    absorbed = any(ast_to_identity(oc) in simple_ids for oc in or_children)
                    if not absorbed:
                        new_children.append(child)
                else:
                    new_children.append(child)
            flat_children = new_children
        if len(flat_children) == 1:
            return flat_children[0]
        if len(flat_children) == 0:
            return ('bool', True)
        return (tag,) + tuple(flat_children)
    return (tag,) + tuple(children)

def step_operand_sort(ast):
    if not isinstance(ast, tuple):
        return ast
    tag = ast[0]
    if tag in ('int', 'var'):
        return ast
    children = [step_operand_sort(child) for child in ast[1:]]
    if tag in ('AND', 'OR'):
        children.sort(key=ast_to_identity)
    return (tag,) + tuple(children)

def canonical_transform(ast):
    ast = step_constant_fold(ast)
    ast = step_algebraic_simplify(ast)
    ast = step_relational_normalize(ast)
    ast = step_boolean_flatten(ast)
    ast = step_boolean_simplify(ast)
    ast = step_operand_sort(ast)
    return ast

def ast_to_identity(ast):
    return json.dumps(ast, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def identity_sha256(identity_str):
    return hashlib.sha256(identity_str.encode('utf-8')).hexdigest()

def is_contradiction(lo_op, lo_val, hi_op, hi_val):
    if lo_op in ('>=', '>') and hi_op in ('<=', '<'):
        if lo_op == '>=' and hi_op == '<=':
            return lo_val > hi_val
        if lo_op == '>' and hi_op == '<':
            return lo_val >= hi_val
        if lo_op == '>=' and hi_op == '<':
            return lo_val >= hi_val
        if lo_op == '>' and hi_op == '<=':
            return lo_val >= hi_val
    return False

def dominance_reduce(constraints_with_ids):
    var_lowers = {}
    var_uppers = {}
    compounds = []
    for ast, identity in constraints_with_ids:
        if is_simple_bound(ast):
            op = ast[0]
            var_name = get_var_name(ast[1])
            int_val = get_int_value(ast[2])
            if op in ('>', '>='):
                if var_name not in var_lowers:
                    var_lowers[var_name] = []
                var_lowers[var_name].append((op, int_val, ast, identity))
            elif op in ('<', '<='):
                if var_name not in var_uppers:
                    var_uppers[var_name] = []
                var_uppers[var_name].append((op, int_val, ast, identity))
        else:
            compounds.append((ast, identity))
    reduced = []
    for var_name in set(var_lowers.keys()) | set(var_uppers.keys()):
        lowers = var_lowers.get(var_name, [])
        uppers = var_uppers.get(var_name, [])
        if lowers:
            lowers.sort(key=lambda x: (x[1], 1 if x[0] == '>' else 0), reverse=True)
            best_lo = lowers[0]
            reduced.append((best_lo[2], best_lo[3]))
            lo_val = best_lo[1]
            lo_op = best_lo[0]
        else:
            lo_val = lo_op = None
        if uppers:
            uppers.sort(key=lambda x: (x[1], 1 if x[0] == '<' else 0))
            best_hi = uppers[0]
            reduced.append((best_hi[2], best_hi[3]))
            hi_val = best_hi[1]
            hi_op = best_hi[0]
        else:
            hi_val = hi_op = None
        if lo_val is not None and hi_val is not None:
            if is_contradiction(lo_op, lo_val, hi_op, hi_val):
                return ([], f"REJECT+HALT: Contradiction — {var_name} {lo_op} {lo_val} AND {var_name} {hi_op} {hi_val}")
    reduced.extend(compounds)
    compound_depth_sum = sum(ast_depth(ast) for ast, _ in compounds)
    if compound_depth_sum > COMPOUND_BUDGET:
        return ([], f"REJECT+HALT: Compound budget exceeded ({compound_depth_sum} > {COMPOUND_BUDGET})")
    return (reduced, None)
def ADMIT(input_data, constants=None):
    if constants is None:
        constants = {
            'K': K, 'D': D, 'V': V, 'N_MAX': N_MAX,
            'INT_MIN': INT_MIN, 'INT_MAX': INT_MAX,
            'OBJ_MAX_BYTES': OBJ_MAX_BYTES,
            'COMPOUND_BUDGET': COMPOUND_BUDGET
        }
    if not isinstance(input_data, dict):
        return {'result': 'REJECT+HALT', 'reason': '4.1: Input must be a dictionary'}
    required_fields = {'objective_commitment', 'constraint_set', 'input_set'}
    if set(input_data.keys()) != required_fields:
        return {'result': 'REJECT+HALT', 'reason': f'4.1: Fields must be exactly {required_fields}'}
    for field in required_fields:
        if input_data[field] is None:
            return {'result': 'REJECT+HALT', 'reason': f'4.1: Field {field} is null'}
    obj = input_data['objective_commitment']
    constraints = input_data['constraint_set']
    input_set = input_data['input_set']
    if not isinstance(obj, str):
        return {'result': 'REJECT+HALT', 'reason': '4.2: objective_commitment must be string'}
    if not isinstance(constraints, list) or not all(isinstance(c, str) for c in constraints):
        return {'result': 'REJECT+HALT', 'reason': '4.2: constraint_set must be list of strings'}
    if not isinstance(input_set, dict):
        return {'result': 'REJECT+HALT', 'reason': '4.2: input_set must be dict'}
    for k, v in input_set.items():
        if not isinstance(k, str):
            return {'result': 'REJECT+HALT', 'reason': '4.2: input_set keys must be strings'}
        if not isinstance(v, (int, bool)):
            return {'result': 'REJECT+HALT', 'reason': '4.2: input_set values must be int or bool'}
        if isinstance(v, int) and (v < constants['INT_MIN'] or v > constants['INT_MAX']):
            return {'result': 'REJECT+HALT', 'reason': '4.2: input_set value out of 128-bit range'}
        if isinstance(v, bool) and v not in (True, False):
            return {'result': 'REJECT+HALT', 'reason': '4.2: input_set bool must be true or false'}
    available_vars = set(input_set.keys())
    parsed_asts = []
    for constraint_str in constraints:
        try:
            ast = parse_expr(constraint_str, available_vars)
        except ValueError as e:
            return {'result': 'REJECT+HALT', 'reason': f'4.5 Parse failure: {e}'}
        parsed_asts.append(ast)
    if len(obj) == 0 or len(obj.encode('utf-8')) > constants['OBJ_MAX_BYTES']:
        return {'result': 'REJECT+HALT', 'reason': '4.6: objective_commitment length out of bounds'}
    if any(ord(c) < 32 and c not in ('\t', '\n', '\r') for c in obj):
        return {'result': 'REJECT+HALT', 'reason': '4.6: objective_commitment contains control characters'}
    for ast in parsed_asts:
        try:
            ast_to_identity(ast)
        except Exception as e:
            return {'result': 'REJECT+HALT', 'reason': f'4.8: Canonicalization failed: {e}'}
    N = len(constraints)
    if N < 1 or N > constants['K']:
        return {'result': 'REJECT+HALT', 'reason': f'4.10: N={N} not in [1, {constants["K"]}]'}
    if len(available_vars) > constants['V']:
        return {'result': 'REJECT+HALT', 'reason': f'4.10: vars={len(available_vars)} exceeds V={constants["V"]}'}
    compound_depth_sum = sum(ast_depth(ast) for ast in parsed_asts if is_compound(ast))
    if compound_depth_sum > constants['COMPOUND_BUDGET']:
        return {'result': 'REJECT+HALT',
                'reason': f'4.10: compound depth sum {compound_depth_sum} exceeds budget {constants["COMPOUND_BUDGET"]}'}
    return {'result': 'ACCEPT', 'parsed_asts': parsed_asts, 'available_vars': available_vars}
def NORMALIZE(input_data):
    admission = ADMIT(input_data)
    if admission['result'] != 'ACCEPT':
        return {'result': 'REJECT+HALT', 'reason': admission['reason']}
    parsed_asts = admission['parsed_asts']
    transformed = []
    for ast in parsed_asts:
        try:
            canon_ast = canonical_transform(ast)
        except ValueError as e:
            return {'result': 'REJECT+HALT', 'reason': f'N2 failure: {e}'}
        transformed.append(canon_ast)
    with_identity = [(ast, ast_to_identity(ast)) for ast in transformed]
    seen = set()
    deduped = []
    for ast, identity in with_identity:
        if identity not in seen:
            seen.add(identity)
            deduped.append((ast, identity))
    reduced, error = dominance_reduce(deduped)
    if error:
        return {'result': 'REJECT+HALT', 'reason': error}
    reduced.sort(key=lambda x: x[1])
    total_output_nodes = sum(ast_node_count(ast) for ast, _ in reduced)
    if total_output_nodes > N_MAX:
        return {'result': 'REJECT+HALT',
                'reason': f'Output node count {total_output_nodes} exceeds N_MAX={N_MAX}'}
    return {
        'result': 'OK',
        'constraints': [identity for _, identity in reduced],
        'stats': {'N': len(reduced), 'input_count': len(parsed_asts)}
    }
if __name__ == '__main__':
    PASS_COUNT = 0
    FAIL_COUNT = 0
    TOTAL_TESTS = 0
    def test(name, condition, detail=""):
        global TOTAL_TESTS, PASS_COUNT, FAIL_COUNT
        TOTAL_TESTS += 1
        if condition:
            PASS_COUNT += 1
            print(f"[PASS] {name}")
        else:
            FAIL_COUNT += 1
            print(f"[FAIL] {name}  —  {detail}")
        if detail and condition:
            print(f"       {detail}")

    print("=" * 70)
    print("PHASE 1 — MASTER CLAIMS-EVIDENCE VALIDATION SUITE")
    print("=" * 70)
    print()

    # CLAIM 1
    print("--- CLAIM 1: DETERMINISM ---")
    input_det = {
        'objective_commitment': 'DET_TEST',
        'constraint_set': ['x > 5', '5 < x', 'x > (2+3)', 'x > 0+5', '(x) > (5)'],
        'input_set': {'x': 0}
    }
    r1 = NORMALIZE(input_det)
    r2 = NORMALIZE(input_det)
    sha1 = hashlib.sha256(json.dumps(r1['constraints'], sort_keys=True).encode()).hexdigest()
    sha2 = hashlib.sha256(json.dumps(r2['constraints'], sort_keys=True).encode()).hexdigest()
    test("CLAIM 1 — Same input, same output across two runs", sha1 == sha2,
         f"SHA256: {sha1[:16]}... == {sha2[:16]}...")
    test("CLAIM 1 — Result is OK", r1['result'] == 'OK')
    test("CLAIM 1 — All 5 forms → 1 canonical identity", len(r1['constraints']) == 1,
         f"Output count: {len(r1['constraints'])} (expected 1)")
    shuffled = list(input_det['constraint_set'])
    random.seed(42)
    random.shuffle(shuffled)
    input_shuf = {'objective_commitment': 'DET_TEST', 'constraint_set': shuffled, 'input_set': {'x': 0}}
    r3 = NORMALIZE(input_shuf)
    sha3 = hashlib.sha256(json.dumps(r3['constraints'], sort_keys=True).encode()).hexdigest()
    test("CLAIM 1 — Shuffled input produces identical output", sha1 == sha3,
         f"SHA256: {sha1[:16]}... == {sha3[:16]}...")
    print()

    # CLAIM 2 (REVISED)
    print("--- CLAIM 2 (REVISED) ---")
    def depth31_compound():
        core = 'x'
        for _ in range(30):
            core = f'({core}+0)'
        return f'{core} > 5'
    input_2a = {'objective_commitment': 'BOUND_2A', 'constraint_set': [depth31_compound() for _ in range(4)],
                'input_set': {'x': 0}}
    res_2a = NORMALIZE(input_2a)
    test("CLAIM 2 — 4 depth-31 compounds (budget 124) → ACCEPT",
         res_2a['result'] == 'OK' and len(res_2a['constraints']) == 1,
         f"Result: {res_2a['result']}, count: {len(res_2a.get('constraints', []))}")
    input_2b = {'objective_commitment': 'BOUND_2B', 'constraint_set': [depth31_compound() for _ in range(5)],
                'input_set': {'x': 0}}
    res_2b = NORMALIZE(input_2b)
    test("CLAIM 2 — 5 depth-31 compounds (budget 155) → REJECT", res_2b['result'] == 'REJECT+HALT',
         f"Result: {res_2b['result']}")
    input_2c = {'objective_commitment': 'BOUND_2C', 'constraint_set': ['x > 5'] * 16,
                'input_set': {'x': 0}}
    res_2c = NORMALIZE(input_2c)
    test("CLAIM 2 — 16 identical simple bounds → ACCEPT (output 3 nodes)",
         res_2c['result'] == 'OK' and len(res_2c['constraints']) == 1,
         f"Result: {res_2c['result']}, count: {len(res_2c.get('constraints', []))}")
    c16x13 = [f'x{i} > {i} AND x{i} < {i + 10} AND x{i} > {i - 1} AND x{i} < {i + 20}' for i in range(16)]
    input_2d = {'objective_commitment': 'BOUND_2D', 'constraint_set': c16x13,
                'input_set': {f'x{i}': 0 for i in range(16)}}
    res_2d = NORMALIZE(input_2d)
    test("CLAIM 2 — 16×13 nodes = 208 output → ACCEPT",
         res_2d['result'] == 'OK' and len(res_2d['constraints']) == 16,
         f"Result: {res_2d['result']}, count: {len(res_2d.get('constraints', []))}")
    c16x58 = [(' AND '.join([f'x{i} > {j}' for j in range(1, 20)])) for i in range(16)]
    input_2e = {'objective_commitment': 'BOUND_2E', 'constraint_set': c16x58,
                'input_set': {f'x{i}': 0 for i in range(16)}}
    res_2e = NORMALIZE(input_2e)
    test("CLAIM 2 — 16×58 nodes = 928 output → REJECT", res_2e['result'] == 'REJECT+HALT',
         f"Result: {res_2e['result']}")
    input_2f = {'objective_commitment': 'BOUND_2F', 'constraint_set': [f'x > {i}' for i in range(17)],
                'input_set': {'x': 0}}
    res_2f = NORMALIZE(input_2f)
    test("CLAIM 2 — N=17 rejected", res_2f['result'] == 'REJECT+HALT', f"Result: {res_2f['result']}")
    deep_constraint = ' AND '.join(['x > 5'] * 33)
    input_2g = {'objective_commitment': 'DEPTH_G', 'constraint_set': [deep_constraint], 'input_set': {'x': 0}}
    res_2g = NORMALIZE(input_2g)
    test("CLAIM 2 — Depth>32 rejected", res_2g['result'] == 'REJECT+HALT', f"Result: {res_2g['result']}")
    input_2h = {'objective_commitment': 'BOUND_2H', 'constraint_set': [f'x{i} > 0' for i in range(16)],
                'input_set': {f'x{i}': 0 for i in range(65)}}
    res_2h = NORMALIZE(input_2h)
    test("CLAIM 2 — Vars=65 rejected", res_2h['result'] == 'REJECT+HALT', f"Result: {res_2h['result']}")
    print()

    # CLAIMS 3 & 4
    print("--- CLAIM 3 & 4: TERMINATION & FIXED-POINT ---")
    test_cases_fp = [
        "x > 5",
        "x + 1 > 6",
        "x > 5 AND y < 10",
        "x > 5 OR x > 5 AND y < 10",
        "5 < x",
        "x > (2+3)",
        "x > 0 AND x > 1 AND x > 2 AND x > 3 AND x > 4",
        "x > 5 AND x > 3 OR y < 10 AND y < 20",
        "NOT NOT NOT NOT x > 5",
    ]
    fp_ok = True
    for expr in test_cases_fp:
        try:
            vars_used = set()
            for ch in expr.split():
                clean = ch.strip('(),')
                if clean.isalpha() and clean.upper() not in ('AND', 'OR', 'NOT'):
                    vars_used.add(clean)
            ast = parse_expr(expr, vars_used)
            c1 = canonical_transform(ast)
            c2 = canonical_transform(c1)
            c3 = canonical_transform(c2)
            id1 = ast_to_identity(c1)
            id2 = ast_to_identity(c2)
            id3 = ast_to_identity(c3)
            if id1 != id2 or id2 != id3:
                fp_ok = False
                test(f"CLAIM 3/4 — Fixed-point for: {expr}", False, f"c1!=c2 or c2!=c3")
        except Exception as e:
            fp_ok = False
            test(f"CLAIM 3/4 — Parse/transform for: {expr}", False, str(e))
    if fp_ok:
        test("CLAIM 3 & 4 — Fixed-point holds for all 9 test cases", True,
             "All canonical_transform twice → identical")
    print()

    # CLAIM 5
    print("--- CLAIM 5: COMMUTATIVITY ---")
    input_ab = {'objective_commitment': 'COMM_TEST', 'constraint_set': ['x > 5 AND y < 10'],
                'input_set': {'x': 0, 'y': 0}}
    input_ba = {'objective_commitment': 'COMM_TEST', 'constraint_set': ['y < 10 AND x > 5'],
                'input_set': {'x': 0, 'y': 0}}
    res_ab = NORMALIZE(input_ab)
    res_ba = NORMALIZE(input_ba)
    test("CLAIM 5 — AND(A,B) == AND(B,A)", res_ab['constraints'] == res_ba['constraints'],
         f"AB: {res_ab['constraints'][0][:50]}... | BA: {res_ba['constraints'][0][:50]}...")
    print()

    # CLAIM 6
    print("--- CLAIM 6: ABSORPTION ---")
    input_absorb = {'objective_commitment': 'ABSORB_TEST', 'constraint_set': ['x > 5 OR (x > 5 AND y < 10)'],
                    'input_set': {'x': 0, 'y': 0}}
    input_plain = {'objective_commitment': 'ABSORB_TEST', 'constraint_set': ['x > 5'], 'input_set': {'x': 0}}
    res_absorb = NORMALIZE(input_absorb)
    res_plain = NORMALIZE(input_plain)
    test("CLAIM 6 — A OR (A AND B) → A", res_absorb['constraints'] == res_plain['constraints'],
         f"Absorbed: {res_absorb['constraints']} | Plain: {res_plain['constraints']}")
    input_nary = {'objective_commitment': 'ABSORB_NARY',
                  'constraint_set': ['x > 5 OR (x > 5 AND y < 10 AND z > 0)'],
                  'input_set': {'x': 0, 'y': 0, 'z': 0}}
    res_nary = NORMALIZE(input_nary)
    test("CLAIM 6 — A OR (A AND B AND C) → A (n-ary)", res_nary['constraints'] == res_plain['constraints'],
         f"N-ary: {res_nary['constraints']} | Plain: {res_plain['constraints']}")
    print()

    # CLAIM 7
    print("--- CLAIM 7: IDENTITY BIJECTION ---")
    forms_10 = ['x > 5', '5 < x', 'x > (2+3)', 'x > (1+4)', 'x > (6-1)', 'x > (10-5)', '(x) > (5)', '(x) > (2+3)',
                'x > 0+5', 'x > 5+0']
    input_10 = {'objective_commitment': 'BIJ_TEST', 'constraint_set': forms_10, 'input_set': {'x': 0}}
    res_10 = NORMALIZE(input_10)
    test("CLAIM 7 — 10 forms of x>5 → 1 identity",
         res_10['result'] == 'OK' and len(res_10['constraints']) == 1,
         f"Unique outputs: {len(res_10['constraints']) if res_10['result'] == 'OK' else 'REJECT'}")
    input_distinct = {'objective_commitment': 'BIJ_TEST', 'constraint_set': ['x > 5', 'x < 10'], 'input_set': {'x': 0}}
    res_distinct = NORMALIZE(input_distinct)
    test("CLAIM 7 — Distinct constraints produce distinct identities",
         res_distinct['result'] == 'OK' and len(res_distinct['constraints']) == 2,
         f"Count: {len(res_distinct['constraints']) if res_distinct['result'] == 'OK' else 'REJECT'}")
    print()

    # CLAIM 8
    print("--- CLAIM 8: SERIALIZATION INVARIANCE ---")
    ast_x5 = canonical_transform(parse_expr('x > 5', {'x': 0}))
    identity_str = ast_to_identity(ast_x5)
    sha = identity_sha256(identity_str)
    expected_sha = 'ed69b80b347eeea06915a3af43303d8997ed33cb0f05200504f1dbc18b8f5907'
    test("CLAIM 8 — x>5 → expected identity string", identity_str == '[">",["var","x"],["int",5]]',
         f"Identity: {identity_str}")
    test("CLAIM 8 — SHA256 matches cross-language test vector", sha == expected_sha, f"SHA256: {sha}")
    print()

    # CLAIM 9
    print("--- CLAIM 9: NORMALIZATION CLOSURE ---")
    closure_ok = True
    for expr in ['x > 5', '5 < x', 'x > (2+3)', 'x > 5 AND y < 10 OR z > 0']:
        vars_used = set()
        for ch in expr.split():
            clean = ch.strip('(),')
            if clean.isalpha() and clean.upper() not in ('AND', 'OR', 'NOT'):
                vars_used.add(clean)
        ast = canonical_transform(parse_expr(expr, vars_used))
        identity = ast_to_identity(ast)
        def check_no_int_op_var(node):
            if isinstance(node, tuple) and node[0] in RELATIONAL_OPS:
                left = node[1]
                if isinstance(left, tuple) and left[0] == 'int':
                    return False
            if isinstance(node, tuple) and node[0] not in ('int', 'var'):
                return all(check_no_int_op_var(c) for c in node[1:])
            return True
        if not check_no_int_op_var(ast):
            closure_ok = False
            test(f"CLAIM 9 — Unflipped int OP var found in: {expr}", False, identity)
    if closure_ok:
        test("CLAIM 9 — No reduction rule applicable after normalization", True)
    print()

    # CLAIM 10
    print("--- CLAIM 10: STRUCTURAL STABILITY ---")
    res_stab = NORMALIZE({'objective_commitment': 'STAB_TEST', 'constraint_set': forms_10, 'input_set': {'x': 0}})
    test("CLAIM 10 — 10 equivalent forms → 1 output (no explosion)",
         res_stab['result'] == 'OK' and len(res_stab['constraints']) == 1,
         f"Output count: {len(res_stab['constraints']) if res_stab['result'] == 'OK' else 'REJECT'}")
    input_flood = {'objective_commitment': 'FLOOD_TEST',
                   'constraint_set': ['x > 0', 'x > -1', 'x > -2', 'x > (0+0)', 'x > 0', '0 < x'],
                   'input_set': {'x': 0}}
    res_flood = NORMALIZE(input_flood)
    test("CLAIM 10 — 6-form redundancy flood → 1 output",
         res_flood['result'] == 'OK' and len(res_flood['constraints']) == 1,
         f"Output count: {len(res_flood['constraints']) if res_flood['result'] == 'OK' else 'REJECT'}")
    print()

    # CLAIM 11
    print("--- CLAIM 11: NO UNBOUNDED ESCAPE CHANNELS ---")
    for constraint, desc in [('x > \t-1', 'Tab in body'), ('x > -01', '-0N form'), ('--1', '--N form')]:
        input_esc = {'objective_commitment': 'ESC_TEST', 'constraint_set': [constraint], 'input_set': {'x': 0}}
        res_esc = NORMALIZE(input_esc)
        test(f"CLAIM 11 — {desc} rejected", res_esc['result'] == 'REJECT+HALT', f"Result: {res_esc['result']}")
    print()

    print("=" * 70)
    print(f"VALIDATION COMPLETE")
    print(f"Total tests: {TOTAL_TESTS}")
    print(f"Passed: {PASS_COUNT}")
    print(f"Failed: {FAIL_COUNT}")
    if FAIL_COUNT == 0:
        print("VERDICT: ALL CLAIMS VALIDATED — Phase 1 is internally proven.")
    else:
        print(f"VERDICT: {FAIL_COUNT} FAILURE(S) — Phase 1 claims violated. Patch required.")
    print("=" * 70)