# Query language

A small filter language for log records, implemented as a lexer, a
recursive-descent parser, and a tree-walking evaluator (`src/logaudit/query.py`).

## Grammar

```
expr       := or_expr
or_expr    := and_expr ("OR" and_expr)*
and_expr   := not_expr ("AND" not_expr)*
not_expr   := "NOT" not_expr | primary
primary    := "(" expr ")" | comparison
comparison := FIELD OP VALUE
OP         := "=" | "!=" | ">" | ">=" | "<" | "<=" | "=~"
VALUE      := NUMBER | STRING | BAREWORD
```

- `AND` binds tighter than `OR`; parentheses override precedence.
- Keywords `AND` / `OR` / `NOT` are case-insensitive.
- `=~` is a regular-expression search (Python `re.search`).

## Values and comparisons

- A comparison is **numeric** when both the field value and the literal parse as
  numbers, otherwise it is a **string** comparison.
- A **missing** field compares unequal to everything: `field=x` is false and
  `field!=x` is true when the field is absent.
- Booleans are never treated as numbers.

## Fields

Field names may be dotted to descend into nested objects:

```
http.status>=500 AND http.method=POST
```

## Examples

```
level=ERROR
level=ERROR AND service=api
code=~"5.."
latency_ms>500 OR level=ERROR
level=ERROR AND (latency_ms>500 OR code=~"5..") AND NOT service=probe
```

## Errors

Malformed queries raise `QueryError` with the offending position, e.g.
`unexpected ')' at position 12` or `unexpected end of query`.
