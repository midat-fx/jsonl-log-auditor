# Security Policy

logaudit processes local files only and makes no network calls. Report any
security issue privately to midat.faizov@gmail.com rather than opening a public
issue. Note that `redact` uses a keyed HMAC to pseudonymise data; supply a
secret key via `--key` or `LOGAUDIT_REDACT_KEY` for real use — the built-in
default key is for demos only and is not secret.
