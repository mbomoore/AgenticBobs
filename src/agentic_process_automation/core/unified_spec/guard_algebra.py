"""
Guard algebra: parse the string predicates used in WorkUnit.preconditions /
WorkUnit.done / ExecutionRule.condition into a small boolean AST, and offer
symbolic queries the design copilot needs:

  - parse(s)     → Expr           (AST)
  - to_sql(s)    → str            (SELECT-1 form for ViewEvaluationEngine)
  - implies(p,q) → Optional[bool] (Z3-backed; None if the predicate is
                                   outside the supported fragment)
  - disjoint(p,q)→ Optional[bool]

The AST covers a deliberately small fragment — boolean literals, AND / OR /
NOT, parentheses, and comparison atoms (=, !=, <, <=, >, >=) against numeric
or single-quoted-string literals. That's enough for the routing predicates
the copilot will reason over; richer SQL (IN, IS NOT NULL, function calls)
is left to the runtime evaluator and excluded from the symbolic layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, Union

from z3 import And as ZAnd
from z3 import BoolVal as ZBoolVal
from z3 import Not as ZNot
from z3 import Or as ZOr
from z3 import Real, Solver, String, StringVal, sat, unsat


# ---------- AST ----------


@dataclass(frozen=True)
class TrueLit:
    pass


@dataclass(frozen=True)
class FalseLit:
    pass


@dataclass(frozen=True)
class Atom:
    field: str
    op: str  # one of: =, !=, <, <=, >, >=
    value: Any  # int | float | str


@dataclass(frozen=True)
class Not_:
    child: "Expr"


@dataclass(frozen=True)
class And_:
    children: Tuple["Expr", ...]


@dataclass(frozen=True)
class Or_:
    children: Tuple["Expr", ...]


Expr = Union[TrueLit, FalseLit, Atom, Not_, And_, Or_]


# ---------- to_sql (drop-in for Interpreter._construct_query_from_predicate) ----------


def to_sql(predicate: str) -> str:
    """
    Wrap a predicate as a SELECT-1 query for ViewEvaluationEngine.

    Preserves the existing Interpreter behaviour:
      - Strings already containing SELECT pass through.
      - Bare predicates must reference an entity via "Entity.field ..." form.
    """
    if "SELECT " in predicate.upper():
        return predicate
    match = re.match(r"(\w+)\.", predicate)
    if not match:
        raise ValueError(f"Invalid predicate format: '{predicate}'")
    entity = match.group(1)
    return f"SELECT 1 FROM {entity} WHERE {predicate}"


# ---------- Parser ----------


_TOKEN_RE = re.compile(
    r"""
    \s*(
        \(                          |
        \)                          |
        (?:AND|OR|NOT|True|False)\b |
        '(?:[^']|'')*'              |   # single-quoted string
        -?\d+\.\d+                  |   # float
        -?\d+                       |   # int
        [<>!]=                      |
        =                           |
        <                           |
        >                           |
        [A-Za-z_][\w\.:]*               # identifier (allows dots and :params)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _tokenize(s: str) -> List[str]:
    tokens: List[str] = []
    pos = 0
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            raise ValueError(f"Cannot tokenise predicate at: {s[pos:]!r}")
        tok = m.group(1)
        tokens.append(tok)
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def consume(self) -> str:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def expect(self, tok: str) -> None:
        actual = self.peek()
        if actual is None or actual.upper() != tok.upper():
            raise ValueError(f"Expected {tok!r}, got {actual!r}")
        self.consume()

    def parse_expr(self) -> Expr:
        node = self.parse_or()
        if self.peek() is not None:
            raise ValueError(f"Unexpected trailing token: {self.peek()!r}")
        return node

    def parse_or(self) -> Expr:
        left = self.parse_and()
        children = [left]
        while self.peek() is not None and self.peek().upper() == "OR":
            self.consume()
            children.append(self.parse_and())
        return left if len(children) == 1 else Or_(tuple(children))

    def parse_and(self) -> Expr:
        left = self.parse_not()
        children = [left]
        while self.peek() is not None and self.peek().upper() == "AND":
            self.consume()
            children.append(self.parse_not())
        return left if len(children) == 1 else And_(tuple(children))

    def parse_not(self) -> Expr:
        if self.peek() is not None and self.peek().upper() == "NOT":
            self.consume()
            return Not_(self.parse_not())
        return self.parse_atom()

    def parse_atom(self) -> Expr:
        tok = self.peek()
        if tok == "(":
            self.consume()
            inner = self.parse_or()
            self.expect(")")
            return inner
        if tok is None:
            raise ValueError("Unexpected end of predicate")
        if tok.upper() == "TRUE":
            self.consume()
            return TrueLit()
        if tok.upper() == "FALSE":
            self.consume()
            return FalseLit()

        field = self.consume()
        if not re.match(r"[A-Za-z_]", field):
            raise ValueError(f"Expected field name, got {field!r}")

        op = self.consume()
        if op not in {"=", "!=", "<", "<=", ">", ">="}:
            raise ValueError(f"Unsupported comparison operator: {op!r}")

        value_tok = self.consume()
        value = _parse_literal(value_tok)
        return Atom(field=field, op=op, value=value)


def _parse_literal(tok: str) -> Any:
    if tok.startswith("'") and tok.endswith("'"):
        return tok[1:-1].replace("''", "'")
    try:
        return int(tok)
    except ValueError:
        pass
    try:
        return float(tok)
    except ValueError:
        pass
    raise ValueError(f"Unsupported literal: {tok!r}")


def parse(predicate: str) -> Expr:
    """Parse a predicate string into an AST.

    Raises ValueError if the predicate falls outside the supported fragment.
    The Interpreter does not call this directly — it uses `to_sql`. This is
    the entry point for symbolic queries (implies, disjoint).
    """
    if "SELECT " in predicate.upper():
        raise ValueError(
            "parse() does not accept full SELECT statements; pass a bare predicate."
        )
    tokens = _tokenize(predicate)
    return _Parser(tokens).parse_expr()


# ---------- Z3 encoding ----------


class _UnsupportedForZ3(Exception):
    """Raised when an Expr uses constructs the symbolic layer can't encode."""


def _to_z3(expr: Expr, var_cache: dict):
    if isinstance(expr, TrueLit):
        return ZBoolVal(True)
    if isinstance(expr, FalseLit):
        return ZBoolVal(False)
    if isinstance(expr, Not_):
        return ZNot(_to_z3(expr.child, var_cache))
    if isinstance(expr, And_):
        return ZAnd(*[_to_z3(c, var_cache) for c in expr.children])
    if isinstance(expr, Or_):
        return ZOr(*[_to_z3(c, var_cache) for c in expr.children])
    if isinstance(expr, Atom):
        return _atom_to_z3(expr, var_cache)
    raise _UnsupportedForZ3(f"Unknown AST node: {expr!r}")


def _atom_to_z3(atom: Atom, var_cache: dict):
    is_string = isinstance(atom.value, str)
    cached = var_cache.get(atom.field)
    if cached is None:
        var = String(atom.field) if is_string else Real(atom.field)
        var_cache[atom.field] = ("str" if is_string else "num", var)
    else:
        prev_kind, var = cached
        new_kind = "str" if is_string else "num"
        if prev_kind != new_kind:
            raise _UnsupportedForZ3(
                f"Field {atom.field!r} compared against mixed types — cannot encode"
            )

    if is_string:
        if atom.op not in {"=", "!="}:
            raise _UnsupportedForZ3(
                f"String field {atom.field!r} only supports = and !="
            )
        eq = var == StringVal(atom.value)
        return eq if atom.op == "=" else ZNot(eq)

    rhs = atom.value
    if atom.op == "=":
        return var == rhs
    if atom.op == "!=":
        return var != rhs
    if atom.op == "<":
        return var < rhs
    if atom.op == "<=":
        return var <= rhs
    if atom.op == ">":
        return var > rhs
    if atom.op == ">=":
        return var >= rhs
    raise _UnsupportedForZ3(f"Unknown operator: {atom.op!r}")


def _check(formula) -> Optional[bool]:
    """Return True if formula is unsat, False if sat, None on unknown."""
    s = Solver()
    s.add(formula)
    result = s.check()
    if result == unsat:
        return True
    if result == sat:
        return False
    return None


def implies(p: str, q: str) -> Optional[bool]:
    """Does predicate p logically imply predicate q?

    Returns True / False, or None if either predicate is outside the
    supported symbolic fragment.
    """
    try:
        p_ast, q_ast = parse(p), parse(q)
        cache: dict = {}
        p_z3 = _to_z3(p_ast, cache)
        q_z3 = _to_z3(q_ast, cache)
    except (ValueError, _UnsupportedForZ3):
        return None
    return _check(ZAnd(p_z3, ZNot(q_z3)))


def disjoint(p: str, q: str) -> Optional[bool]:
    """Are predicates p and q mutually exclusive?

    Returns True / False, or None if either is outside the supported fragment.
    """
    try:
        p_ast, q_ast = parse(p), parse(q)
        cache: dict = {}
        p_z3 = _to_z3(p_ast, cache)
        q_z3 = _to_z3(q_ast, cache)
    except (ValueError, _UnsupportedForZ3):
        return None
    return _check(ZAnd(p_z3, q_z3))
