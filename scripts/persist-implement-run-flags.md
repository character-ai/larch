# persist-implement-run-flags.sh

Writes `$IMPLEMENT_TMPDIR/run-flags.sh` (KV lines) atomically. Sanctioned writer for **`NO_ISSUES`** and **`WORKFLOW_PATH`** consumed by `skills/implement/scripts/write-final-report.sh` (mode display and workflow path in the rich summary). **`QUICK_MODE`** remains in the file for legacy tmpdir compatibility but is not read by `write-final-report.sh` and does not control `/implement` (removed quick mode).

## Interface

```text
persist-implement-run-flags.sh --implement-tmpdir PATH \
  --quick-mode true|false --no-issues true|false --workflow-path SIMPLE|HARD|N/A
```

- **`--workflow-path`** — must be exactly `SIMPLE`, `HARD`, or `N/A` (matches post-plan router semantics).

## Contract

- Exit **2** on validation failure (bad flags, missing tmpdir).
- On success: prints `RUN_FLAGS_PERSISTED=true` to stdout and leaves `run-flags.sh` in place.

Do not compose `run-flags.sh` from prompt-side shell; use this helper so `/implement` Step 2+ reporting stays aligned with the post-plan router.
