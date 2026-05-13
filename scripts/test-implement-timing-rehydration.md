# scripts/test-implement-timing-rehydration.sh — contract

`scripts/test-implement-timing-rehydration.sh` is a structural regression harness for `/implement`'s timing-ledger rehydration blocks.

It rejects the stale two-key export (`LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE`), requires the timing-aware export with `LARCH_TIMING_LEDGER` in every post-Step-0 rehydration block, and cross-checks that every token-session rehydration has matching `LARCH_TIMING_LEDGER` plus `IMPLEMENT_TMPDIR` assignment/export lines. The `IMPLEMENT_TMPDIR` export is load-bearing because `scripts/timing-ledger.sh` validates `LARCH_TIMING_LEDGER` against known session roots.

Wired into `make lint` via `make test-implement-timing-rehydration` and the `test-harnesses` umbrella. Listed in `agent-lint.toml` as a Makefile-only harness.
