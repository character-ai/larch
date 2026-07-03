# scripts/test-deny-edit-write.sh — contract

Regression harness for `scripts/deny-edit-write.sh`, the token-gated PreToolUse hook used by `/research` and `/bug`. The harness isolates `XDG_CACHE_HOME` so local activation sentinels cannot affect results.

The table covers inactive, active, stale, cross-token, tokenless-inactive, foreign-PID, unset-`HOME`, NotebookEdit, path-canonicalization, idempotency, and `jq`-absent-active cases. The full contract, including the byte-identity check on the deny envelope, is owned by `scripts/deny-edit-write.md`.

Wired into `make lint` via the `test-deny-edit-write` target. Listed in `agent-lint.toml`'s exclude set. Edits to either side must stay in sync in the same PR.
