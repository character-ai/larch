# flush-execution-issues.sh

`flush-execution-issues.sh` appends `$IMPLEMENT_TMPDIR/execution-issues.md` to
the committed `execution-issues` larch-log batch before the pre-ship phase.
Primary caller: `/implement` Step 7a pre-ship log flush.

Usage:

```bash
flush-execution-issues.sh \
  --log-root PATH \
  --run-id RUN_ID \
  --issue-log PATH \
  [--batch execution-issues]
```

`--log-root` must be absolute. `--run-id` is restricted to letters, numbers, and
hyphens before constructing `PATH/implement/RUN_ID/execution-issues.ndjson`.
`--skill` is hardcoded to `implement`.

Output envelope:

- `FLUSH_STATUS=skip|already-flushed|no-records|ok|failed`
- `RECORDS=<N>`
- `APPEND_LOG_FILE=<path>` when an append was attempted or failed during record
  composition; the emitted file path remains readable after process exit

Optional flags:

- `--step-label VALUE` overrides the default record step (`7a`)
- `--source-label VALUE` overrides the default record source

Invariants:

- Empty or absent `--issue-log` is a successful skip.
- Default Step 7a calls create `$IMPLEMENT_TMPDIR/.execution-issues-step7a-reached`
  (or the issue-log directory equivalent) even when the flush is a skip, so
  later commit-tail / pre-push helpers know the pre-ship checkpoint already ran.
- Idempotency uses both `$IMPLEMENT_TMPDIR/.execution-issues-flushed.sha` and an
  existing batch `source_sha256` probe. When the sentinel is missing, the batch
  probe matches the normalized per-section hashes that `write_execution_issues_records`
  stores, with a whole-file SHA fallback for backward compatibility.
- Records are composed by `python/cli.py execution-issues flush` with
  `step="7a"` and `source="execution-issues.md pre-bump"` (historical label;
  no version bump occurs — kept for data contract compatibility) unless
  overridden by `--step-label` / `--source-label`.
- On `FLUSH_STATUS=ok` or `FLUSH_STATUS=no-records`, the flushed
  `execution-issues.md` file is cleared so later flushes append only the
  unflushed tail entries.
- `run-log append` failures are non-fatal to `/implement`: the helper logs
  the captured append output back to `execution-issues.md` through
  `run-log append-failure` and exits 1 so the caller can record a wrapper
  failure if desired.

Makefile wiring: `make test-flush-execution-issues`, included in
`test-harnesses-3` alongside `test-implement-finalize`.

Harness coverage: empty input, single-section record composition, multi-section
record composition, idempotent rerun, and `run-log` failure logging.

Edit In Sync:

- `python/larch/issue/execution_issues.py`
- `python3 python/cli.py implement-finalize`
- `skills/implement/SKILL.md`
