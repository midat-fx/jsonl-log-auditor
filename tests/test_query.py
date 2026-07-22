from __future__ import annotations

import pytest

from logaudit.query import QueryError, compile_query


def m(expr: str, rec: dict) -> bool:
    return compile_query(expr).matches(rec)


REC = {"level": "ERROR", "service": "api", "code": 500, "latency_ms": 250, "msg": "boom"}


def test_simple_eq() -> None:
    assert m("level=ERROR", REC)
    assert not m("level=INFO", REC)


def test_neq() -> None:
    assert m("service!=web", REC)
    assert not m("service!=api", REC)


def test_numeric_comparisons() -> None:
    assert m("latency_ms>200", REC)
    assert m("latency_ms>=250", REC)
    assert not m("latency_ms>250", REC)
    assert m("code<=500", REC)
    assert not m("code<500", REC)


def test_regex_match() -> None:
    assert m('code=~"5.."', REC)
    assert m('msg=~"^bo"', REC)
    assert not m('msg=~"^xy"', REC)


def test_and_or_not() -> None:
    assert m("level=ERROR AND service=api", REC)
    assert not m("level=ERROR AND service=web", REC)
    assert m("level=INFO OR code=500", REC)
    assert m("NOT service=web", REC)
    assert not m("NOT level=ERROR", REC)


def test_precedence_and_binds_tighter_than_or() -> None:
    # OR of (INFO AND api) with (code=500): the AND is false, OR rescues via code.
    assert m("level=INFO AND service=api OR code=500", REC)
    # Parentheses change the meaning:
    assert not m("level=INFO AND (service=api OR code=500)", REC)


def test_parentheses_and_compound() -> None:
    assert m('level=ERROR AND (latency_ms>500 OR code=~"5..") AND NOT service=probe', REC)


def test_missing_field() -> None:
    assert not m("missing=1", REC)
    assert m("missing!=1", REC)  # missing != anything is true


def test_dotted_field() -> None:
    rec = {"http": {"status": 500}}
    assert m("http.status=500", rec)
    assert not m("http.status=200", rec)
    assert not m("http.missing=1", rec)


def test_quoted_string_value_with_spaces() -> None:
    assert m('msg=~"handling request"', {"msg": "handling request now"})


@pytest.mark.parametrize(
    "expr",
    ["level=", "AND level=x", "level==x", "(level=x", "level=x)", "", "level x", "=x"],
)
def test_malformed_queries_raise(expr: str) -> None:
    with pytest.raises(QueryError):
        compile_query(expr)


def test_error_reports_position() -> None:
    with pytest.raises(QueryError) as ei:
        compile_query("level=ERROR AND ")
    assert "end of query" in str(ei.value)
