# test-flush-vendor-failure-diagnostics.sh

Offline regression harness for `scripts/flush-vendor-failure-diagnostics.sh`
(#3713). Covers: missing-tmpdir skip, no-parts clear-after-success (no batch
file), per-slot parts merge (sorted, deterministic), idempotent re-flush (no
duplication), and the `--log-root` / `--run-id` batch-staging path via
`larch-log.sh`.

Run:

```bash
bash scripts/test-flush-vendor-failure-diagnostics.sh
```

Or `make test-flush-vendor-failure-diagnostics`.

Referenced only from the Makefile (`test-flush-vendor-failure-diagnostics`
target, `test-harnesses-7` shard) and this sibling contract, matching the
Makefile-only harness pattern; excluded from agent-lint's G004 dead-script rule
in `agent-lint.toml`.
