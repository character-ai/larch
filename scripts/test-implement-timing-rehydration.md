# scripts/test-implement-timing-rehydration.sh — contract

`scripts/test-implement-timing-rehydration.sh` is a structural regression harness for `/implement`'s timing-ledger rehydration blocks.

## Invariants enforced

1. **No stale two-key exports.** Any `export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE` line missing `LARCH_TIMING_LEDGER` is a failure.
2. **Adjacency.** Every fenced ` ```bash ` block (including indented ones inside list items) in `skills/implement/SKILL.md` that invokes `timing-ledger.sh` or `timing-report.sh` MUST contain — inside the SAME fence — an `LARCH_TIMING_LEDGER=$(... read-session-env-key.sh ...)` rehydration line. Step 0's canonical static export (`export LARCH_TIMING_LEDGER="$IMPLEMENT_TMPDIR/timing-ledger.tsv"`) is exempt because it is the source-of-truth write, not a rehydration. This invariant is the one that catches the workflow-path one-liner regression where a standalone `timing-ledger.sh workflow-path "SIMPLE"` block lacks per-run ledger isolation.
3. **Cardinality.** The count of `LARCH_TIMING_LEDGER=` rehydration reads equals the count of `LARCH_TOKEN_SESSION_ID=` rehydration reads, equals the count of the three-key `export` line, equals the count of `IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"` assignments, equals the count of `export IMPLEMENT_TMPDIR` lines. `IMPLEMENT_TMPDIR` is load-bearing because `scripts/timing-ledger.sh` validates `LARCH_TIMING_LEDGER` against `timing_allowed_roots` (which only includes `IMPLEMENT_TMPDIR` when it is env-set).

## Wiring

Wired into `make lint` via `make test-implement-timing-rehydration` and the `test-harnesses` umbrella. Listed in `agent-lint.toml` as a Makefile-only harness.

## Why both invariants 2 and 3

Cardinality alone (invariant 3) does not prove rehydration precedes each ledger call — counts can stay matched while a stray export drifts away from its `timing-ledger.sh` site. Adjacency alone (invariant 2) does not catch a missing `IMPLEMENT_TMPDIR` export (which silently breaks `validate_env_ledger`'s allowed-root check). Together they cover both the "fence covered" and "template complete" requirements.
