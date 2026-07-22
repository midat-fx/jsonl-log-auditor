from __future__ import annotations

from logaudit.schema import validate_record

SCHEMA = {
    "required": ["ts", "level"],
    "properties": {
        "level": {"type": "string", "enum": ["INFO", "ERROR"]},
        "code": {"type": "integer", "minimum": 100, "maximum": 599},
        "ts": {"type": "string", "format": "date-time"},
        "email": {"type": "string", "format": "email"},
        "name": {"type": "string", "minLength": 2, "maxLength": 5},
    },
}
OK = {"ts": "2026-01-01T00:00:00", "level": "INFO"}


def test_valid() -> None:
    assert validate_record(OK, SCHEMA) == []


def test_required_missing() -> None:
    v = validate_record({"level": "INFO"}, SCHEMA)
    assert any("ts" in x and "required" in x for x in v)


def test_enum() -> None:
    v = validate_record({**OK, "level": "LOUD"}, SCHEMA)
    assert any("enum" in x for x in v)


def test_type_mismatch() -> None:
    v = validate_record({**OK, "code": "x"}, SCHEMA)
    assert any("type" in x for x in v)


def test_bool_is_not_integer() -> None:
    v = validate_record({**OK, "code": True}, SCHEMA)
    assert any("type" in x for x in v)


def test_minimum() -> None:
    assert any("minimum" in x for x in validate_record({**OK, "code": 99}, SCHEMA))


def test_maximum() -> None:
    assert any("maximum" in x for x in validate_record({**OK, "code": 600}, SCHEMA))


def test_format_email() -> None:
    assert any("email" in x for x in validate_record({**OK, "email": "nope"}, SCHEMA))


def test_format_datetime() -> None:
    assert any("date-time" in x for x in validate_record({**OK, "ts": "nope"}, SCHEMA))


def test_length_bounds() -> None:
    assert any("minLength" in x for x in validate_record({**OK, "name": "x"}, SCHEMA))
    assert any("maxLength" in x for x in validate_record({**OK, "name": "toolong"}, SCHEMA))
