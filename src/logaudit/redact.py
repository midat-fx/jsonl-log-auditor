"""Deterministic PII redaction.

Sensitive substrings are replaced by ``<tag:token>`` where the token is a short
HMAC-SHA256 of the matched text under a key. The mapping is stable (the same
input and key always produce the same token) so redacted logs remain joinable,
but the original value cannot be recovered. The key is never written out.
"""

from __future__ import annotations

import hmac
import re
from collections.abc import Callable
from hashlib import sha256
from typing import Any

Record = dict[str, Any]

DEFAULT_PATTERNS: dict[str, str] = {
    "email": r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "card": r"\b\d{13,16}\b",
}


def _token(key: bytes, matched: str) -> str:
    return hmac.new(key, matched.encode("utf-8"), sha256).hexdigest()[:10]


def build_redactor(
    key: bytes, patterns: dict[str, str] | None = None
) -> list[tuple[str, re.Pattern[str]]]:
    pats = patterns if patterns is not None else DEFAULT_PATTERNS
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for name, rx in sorted(pats.items()):
        try:
            compiled.append((name, re.compile(rx)))
        except re.error as e:
            raise ValueError(f"invalid redaction pattern {name!r}: {e}") from e
    return compiled


def redact_text(text: str, key: bytes, rules: list[tuple[str, re.Pattern[str]]]) -> str:
    def _replacer(name: str) -> Callable[[re.Match[str]], str]:
        def repl(m: re.Match[str]) -> str:
            return f"<{name}:{_token(key, m.group(0))}>"

        return repl

    for name, rx in rules:
        text = rx.sub(_replacer(name), text)
    return text


def redact_value(value: Any, key: bytes, rules: list[tuple[str, re.Pattern[str]]]) -> Any:
    if isinstance(value, str):
        return redact_text(value, key, rules)
    if isinstance(value, dict):
        return {k: redact_value(v, key, rules) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v, key, rules) for v in value]
    return value


def redact_record(rec: Record, key: bytes, rules: list[tuple[str, re.Pattern[str]]]) -> Record:
    result = redact_value(rec, key, rules)
    assert isinstance(result, dict)
    return result
