# scripts/test-redact-secrets.sh — contract

Regression harness for `scripts/redact-secrets.sh`. Wired into `make lint` via the `test-redact` target. The full contract — pattern set, trailing-quote semantics, idempotency invariant — is owned by `scripts/redact-secrets.md` and `SECURITY.md`'s outbound-redaction subsection. Edits to either side must stay in sync in the same PR.
