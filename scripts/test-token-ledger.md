# test-token-ledger.sh

**Purpose**: Offline regression harness for `scripts/token-ledger.sh`.

It covers mark / record-vendor / dump, JSONL well-formedness, ledger mode `600`, session-id precedence (`LARCH_TOKEN_SESSION_ID` over `$IMPLEMENT_TMPDIR/session-id` over fallback), hashed unsafe ids, `--ledger` containment under `${TMPDIR:-/tmp}`, and JSON safety for quoted/newline `raw=` values.

Run via `make test-token-ledger` or the shard that includes it.

Update this harness when `token-ledger.sh` changes its subcommands, JSON schema, session-id resolution, or path validation.
