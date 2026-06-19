# scripts/flush-vendor-failure-diagnostics.sh — contract

Merge per-slot vendor failure-diagnostic parts into the canonical batch file and
(when a log root + run id are given) stage the `vendor-failure-diagnostics`
larch-log batch. Part of the #3713 vendor-agent diagnostics carrier work.

## Why

Vendor-agent launch failures compose a bounded `${OUTPUT}.failure-diag` carrier
(see `python/agents.py`). Site-aware callers append the
resolved carrier to a durable implement batch via
`append_vendor_failure_diagnostics`, which writes a redacted **per-slot part
file** under `$IMPLEMENT_TMPDIR/vendor-failure-diagnostics.parts/`. Per-slot
staging avoids interleaved concurrent appends without requiring `flock` (absent
on macOS / Bash 3.2). This helper turns those parts into the single committed
batch artifact.

## Interface

```text
flush-vendor-failure-diagnostics.sh --tmpdir DIR [--run-id ID --log-root DIR] [--skill NAME]
```

- `--tmpdir` (required): the run tmpdir holding `vendor-failure-diagnostics.parts/`.
- `--run-id` / `--log-root`: when both are set, the derived batch file is staged
  via `python3 python/cli.py run-log write --batch vendor-failure-diagnostics`.
- `--skill` (default `implement`): larch-log skill namespace.

## Behavior

1. **Clear-after-success**: when the parts directory has no `part.*` files,
   nothing is flushed and no batch is written — a successful run with no
   vendor-agent failures commits nothing (preserves #3534 intent).
2. **Idempotent derive**: the canonical `$tmpdir/vendor-failure-diagnostics.txt`
   is overwritten from the full sorted parts set on every flush, so repeated
   pre-commit flushes converge. The batch slug is `replace` mode
   (`docs/run-log-batches.md`) for the same reason.
3. **Stage only — never commit**: `python3 python/cli.py run-log write` stages the batch under the
   log root; the surrounding flush/refresh sites own the commit, and
   `python3 python/cli.py run-log commit` enforces the post-merge sentinel guard (NEVER #16). This
   helper makes no git commit, so it is safe to call post-merge (it becomes a
   no-op stage).

## Output

`FLUSH_STATUS=empty|skipped|flushed` plus `PARTS=<n>` and (on flush)
`BATCH_WRITTEN=true|false`. All paths exit 0 (best-effort).

## Callers

Called best-effort before each log commit / push:
- `skills/implement/scripts/step-7a.sh` (pre-ship flush)
- `python3 python/cli.py run-log flush` (commit-tail flush)
- `python3 python/cli.py run-log refresh` (CI-retry / rebase pre-push refresh)
- `python3 python/cli.py implement-finalize` teardown (safety net, mirrors
  `flush_execution_issues_safety_net`, F13)

## Invariants

- Bash 3.2 portable (no associative arrays / `mapfile`).
- Never makes a git commit.
- Best-effort: a `python3 python/cli.py run-log write` failure is reported via
  `BATCH_WRITTEN=false`, not a non-zero exit.

## Harness

`scripts/test-flush-vendor-failure-diagnostics.sh` — Makefile target
`test-flush-vendor-failure-diagnostics`.

## Edit-in-sync

Keep aligned with `python/agents.py`
(`append_vendor_failure_diagnostics` part-file layout),
`docs/run-log-batches.md` (the `vendor-failure-diagnostics` slug), and
`docs/vendor-agent-diagnostics-audit.md`.
