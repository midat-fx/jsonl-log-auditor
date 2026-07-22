from __future__ import annotations

from logaudit.redact import build_redactor, redact_record, redact_text

KEY = b"testkey"


def test_deterministic_and_joinable() -> None:
    rules = build_redactor(KEY)
    out = redact_text("ip 10.0.0.5 again 10.0.0.5", KEY, rules)
    tokens = [t for t in out.split() if t.startswith("<ipv4:")]
    assert len(tokens) == 2 and tokens[0] == tokens[1]  # same value -> same token


def test_email_and_ip_masked() -> None:
    rules = build_redactor(KEY)
    out = redact_text("mail a@b.com from 1.2.3.4", KEY, rules)
    assert "<email:" in out and "<ipv4:" in out
    assert "a@b.com" not in out and "1.2.3.4" not in out


def test_different_key_different_token() -> None:
    t1 = redact_text("1.2.3.4", b"k1", build_redactor(b"k1"))
    t2 = redact_text("1.2.3.4", b"k2", build_redactor(b"k2"))
    assert t1 != t2


def test_nested_structures() -> None:
    rules = build_redactor(KEY)
    rec = redact_record({"a": {"b": "x@y.com"}, "l": ["1.2.3.4"]}, KEY, rules)
    assert "<email:" in rec["a"]["b"] and "<ipv4:" in rec["l"][0]
