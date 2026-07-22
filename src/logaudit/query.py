"""A small filter language for log records.

Grammar (recursive descent, left-associative AND/OR)::

    expr       := or_expr
    or_expr    := and_expr ("OR" and_expr)*
    and_expr   := not_expr ("AND" not_expr)*
    not_expr   := "NOT" not_expr | primary
    primary    := "(" expr ")" | comparison
    comparison := FIELD OP VALUE
    OP         := "=" | "!=" | ">" | ">=" | "<" | "<=" | "=~"
    VALUE      := NUMBER | STRING | BAREWORD

``=~`` is a regex search. Comparisons are numeric when both sides look numeric,
otherwise string. Dotted fields (``a.b``) descend into nested objects. A missing
field compares unequal to everything except via ``!=``.

Example::

    level=error AND (latency_ms>500 OR code=~"5..") AND NOT service=probe

See docs/query-language.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

Record = dict[str, Any]


class QueryError(ValueError):
    """Raised on a malformed query, with the offending position when known."""


# ---- lexer ------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<OP>!=|>=|<=|=~|=|>|<)
    | (?P<NUMBER>-?\d+\.\d+|-?\d+)
    | (?P<STRING>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
    | (?P<WORD>[A-Za-z_][\w.\-]*)
    """,
    re.VERBOSE,
)
_KEYWORDS = {"AND", "OR", "NOT"}


@dataclass
class Token:
    kind: str
    value: str
    pos: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    while i < len(text):
        m = _TOKEN_RE.match(text, i)
        if not m:
            raise QueryError(f"unexpected character {text[i]!r} at position {i}")
        i = m.end()
        kind = m.lastgroup or ""
        if kind == "WS":
            continue
        value = m.group()
        if kind == "WORD" and value.upper() in _KEYWORDS:
            kind = value.upper()
        tokens.append(Token(kind, value, m.start()))
    return tokens


# ---- AST --------------------------------------------------------------------


@dataclass
class Cmp:
    field: str
    op: str
    value: Any  # float for NUMBER, str otherwise


@dataclass
class Not:
    child: Node


@dataclass
class And:
    left: Node
    right: Node


@dataclass
class Or:
    left: Node
    right: Node


Node = Cmp | Not | And | Or


# ---- parser -----------------------------------------------------------------


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks = tokens
        self.i = 0

    def _peek(self) -> Token | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _next(self) -> Token:
        tok = self._peek()
        if tok is None:
            raise QueryError("unexpected end of query")
        self.i += 1
        return tok

    def parse(self) -> Node:
        node = self._or()
        if self.i != len(self.toks):
            tok = self.toks[self.i]
            raise QueryError(f"unexpected {tok.value!r} at position {tok.pos}")
        return node

    def _or(self) -> Node:
        node = self._and()
        while (t := self._peek()) is not None and t.kind == "OR":
            self._next()
            node = Or(node, self._and())
        return node

    def _and(self) -> Node:
        node = self._not()
        while (t := self._peek()) is not None and t.kind == "AND":
            self._next()
            node = And(node, self._not())
        return node

    def _not(self) -> Node:
        t = self._peek()
        if t is not None and t.kind == "NOT":
            self._next()
            return Not(self._not())
        return self._primary()

    def _primary(self) -> Node:
        t = self._peek()
        if t is None:
            raise QueryError("unexpected end of query")
        if t.kind == "LPAREN":
            self._next()
            node = self._or()
            close = self._next()
            if close.kind != "RPAREN":
                raise QueryError(f"expected ')' at position {close.pos}")
            return node
        return self._comparison()

    def _comparison(self) -> Cmp:
        field = self._next()
        if field.kind != "WORD":
            raise QueryError(f"expected a field name at position {field.pos}, got {field.value!r}")
        op = self._next()
        if op.kind != "OP":
            raise QueryError(f"expected an operator at position {op.pos}, got {op.value!r}")
        val = self._next()
        if val.kind == "NUMBER":
            value: Any = float(val.value)
        elif val.kind == "STRING":
            value = val.value[1:-1].replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
        elif val.kind in ("WORD", "AND", "OR", "NOT"):
            value = val.value
        else:
            raise QueryError(f"expected a value at position {val.pos}, got {val.value!r}")
        return Cmp(field.value, op.value, value)


# ---- evaluation -------------------------------------------------------------


def _resolve(rec: Record, field: str) -> Any:
    cur: Any = rec
    for part in field.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _as_num(x: Any) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


def _compare(recval: Any, op: str, literal: Any) -> bool:
    if op == "=~":
        return recval is not None and re.search(str(literal), str(recval)) is not None
    if recval is None:
        return op == "!="
    ln, rn = _as_num(recval), _as_num(literal)
    if ln is not None and rn is not None:
        left: Any
        right: Any
        left, right = ln, rn
    else:
        left, right = str(recval), str(literal)
    if op == "=":
        return bool(left == right)
    if op == "!=":
        return bool(left != right)
    if op == ">":
        return bool(left > right)
    if op == ">=":
        return bool(left >= right)
    if op == "<":
        return bool(left < right)
    if op == "<=":
        return bool(left <= right)
    raise QueryError(f"unknown operator {op!r}")


def _eval(node: Node, rec: Record) -> bool:
    if isinstance(node, Cmp):
        return _compare(_resolve(rec, node.field), node.op, node.value)
    if isinstance(node, Not):
        return not _eval(node.child, rec)
    if isinstance(node, And):
        return _eval(node.left, rec) and _eval(node.right, rec)
    return _eval(node.left, rec) or _eval(node.right, rec)


@dataclass
class Query:
    ast: Node

    def matches(self, rec: Record) -> bool:
        return _eval(self.ast, rec)


def compile_query(text: str) -> Query:
    tokens = tokenize(text)
    if not tokens:
        raise QueryError("empty query")
    return Query(_Parser(tokens).parse())
