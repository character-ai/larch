# python/cleanup_implement_logs.py contract

`python3 python/cli.py run-log cleanup-implement-logs` applies retroactive cleanup rules to committed implement run-log directories.

## CLI

Dry-run is the default:

```bash
python3 python/cli.py run-log cleanup-implement-logs
```

Apply changes with:

```bash
python3 python/cli.py run-log cleanup-implement-logs --execute
```

Restrict to one run directory with:

```bash
python3 python/cli.py run-log cleanup-implement-logs --run-dir larch-logs/implement/<UUID> --execute
```

## Invariants

- No file changes occur without `--execute`.
- `--run-dir` must resolve to a path inside `larch-logs/implement/`; an argument that escapes that tree (via `..` or a symlink) is rejected with exit code 1 and no files are touched.
- The summary counters and exit codes stay stable.
- Transcript upgrade, breadcrumb consolidation, tally body stripping, refresh-sidecar cleanup, and obsolete prompt/output deletion remain file-based operations.

## Edit-in-sync

Update this contract with cleanup rule changes.
