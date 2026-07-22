"""A small, self-contained JSON Schema subset validator.

Supported keywords: ``required``, ``properties``, ``type``, ``enum``,
``pattern``, ``minimum``/``maximum``, ``minLength``/``maxLength``, and
``format`` (``date-time``, ``ipv4``, ``email``). Documented in
docs/schema-subset.md. This intentionally avoids a third-party dependency; it is
not a complete JSON Schema implementation.
"""

from __future__ import annotations

import re
from typing import Any

Record = dict[str, Any]

_FORMATS = {
    "date-time": re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"),
    "ipv4": re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$"),
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
}

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def _check_property(name: str, value: Any, spec: dict[str, Any]) -> list[str]:
    out: list[str] = []
    t = spec.get("type")
    if t is not None:
        check = _TYPE_CHECKS.get(t)
        if check is None:
            out.append(f"{name}: schema uses unknown type {t!r}")
        elif not check(value):
            out.append(f"{name}: expected type {t}, got {type(value).__name__}")
            return out  # further checks assume the right type
    if "enum" in spec and value not in spec["enum"]:
        out.append(f"{name}: value {value!r} not in enum {spec['enum']}")
    if "pattern" in spec and isinstance(value, str):
        try:
            matched = re.search(spec["pattern"], value) is not None
        except re.error as e:
            out.append(f"{name}: schema has an invalid pattern {spec['pattern']!r} ({e})")
        else:
            if not matched:
                out.append(f"{name}: value {value!r} does not match pattern {spec['pattern']}")
    fmt = spec.get("format")
    if fmt and isinstance(value, str):
        rx = _FORMATS.get(fmt)
        if rx is not None and not rx.match(value):
            out.append(f"{name}: value {value!r} is not a valid {fmt}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in spec and value < spec["minimum"]:
            out.append(f"{name}: {value} < minimum {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            out.append(f"{name}: {value} > maximum {spec['maximum']}")
    if isinstance(value, str):
        if "minLength" in spec and len(value) < spec["minLength"]:
            out.append(f"{name}: length {len(value)} < minLength {spec['minLength']}")
        if "maxLength" in spec and len(value) > spec["maxLength"]:
            out.append(f"{name}: length {len(value)} > maxLength {spec['maxLength']}")
    return out


def validate_record(rec: Record, schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable violations (empty if the record is valid)."""
    out: list[str] = []
    for name in schema.get("required", []):
        if name not in rec:
            out.append(f"{name}: required property missing")
    props: dict[str, Any] = schema.get("properties", {})
    for name, spec in props.items():
        if name in rec:
            out.extend(_check_property(name, rec[name], spec))
    return out
