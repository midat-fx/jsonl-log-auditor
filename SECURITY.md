# Security Policy

Report any security issue privately to midat.faizov@gmail.com rather than opening
a public issue.

## Threat model

logaudit is a local command-line tool. It:

- makes **no network calls** and opens no sockets;
- performs **no code execution**: no `eval`/`exec`, no `pickle` or other unsafe
  deserialization, no shelling out. JSON is parsed with the standard library.

The queries, schemas, and redaction rule-sets you pass are treated as **trusted
operator input** — like configuration. In particular:

- **Regular expressions** (`query =~`, schema `pattern`, redaction rules) are
  compiled from operator-supplied text. A deliberately pathological regex can
  backtrack (ReDoS); an invalid one is reported as a clean error rather than a
  crash. Do not run untrusted regexes against attacker-controlled data.
- **Compressed input** (`.gz`) is streamed, but a decompression bomb can still
  exhaust memory. Do not point logaudit at untrusted archives without limits.

## Redaction

`redact` pseudonymises matched values with a keyed HMAC-SHA256. Supply a secret
key via `--key` or `LOGAUDIT_REDACT_KEY`; the built-in default key is for demos
only and is not secret. The key is never written to output.
