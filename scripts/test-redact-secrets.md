# scripts/test-redact-secrets.sh — contract

Regression harness for `scripts/redact-secrets.sh`. Wired into `make lint` via
the `test-redact` target. Coverage includes direct token-family redaction,
idempotency, issue-creation integration, and streaming-mode PEM handling:
complete PEM blocks, PEM bodies split across invocations via `--state-file`,
and a fresh-state tail that starts at an `END ... PRIVATE KEY` line.

The full contract — pattern set, trailing-quote semantics, idempotency
invariant, and streaming PEM state — is owned by `scripts/redact-secrets.md`
and `SECURITY.md`'s outbound-redaction subsection. Edits to either side must
stay in sync in the same PR.
