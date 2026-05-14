# refresh-run-logs.sh

Re-renders the `token-report` and `timing-report` larch-log batches from the
current session state and commits the updated files to the branch, so every push
(rebase, CI-fix, version-bump retry) carries up-to-date log artifacts.

## Interface

```text
refresh-run-logs.sh --state-file PATH --implement-tmpdir PATH
```

- `--state-file` — path to `ship-pr-state.sh`; must exist and be readable.
- `--implement-tmpdir` — path to the implement session tmpdir.

## Stdout contract

One `KEY=value` line:

| Key | Values | Meaning |
|-----|--------|---------|
| `REFRESH_COMMITTED` | `true` | Committed updated log files. |
| `REFRESH_COMMITTED` | `false REASON=no-changes` | No staged diff after write; no commit made. |
| `REFRESH_SKIPPED` | `true REASON=post-merge` | State file shows `MERGE_RESULT=merged\|admin_merged\|already_merged`; skipped (safety). |
| `REFRESH_SKIPPED` | `true REASON=invalid-run-id` | `RUN_ID` contains path-traversal characters; skipped. |
| `REFRESH_SKIPPED` | `true REASON=state-file-missing-fail-closed` | State file absent; skipped (fail-closed). |
| `REFRESH_SKIPPED` | `true REASON=no-run-id` | `RUN_ID` absent in state file. |
| `REFRESH_SKIPPED` | `true REASON=no-logs-commit` | `NO_LOGS_COMMIT=true` in state; skipped. |

Always exits 0.

## Invariants

- **Fail-closed post-merge guard**: reads `MERGE_RESULT` from `ship-pr-state.sh`. When
  the key holds `merged` or `admin_merged`, exits 0 with no commit. When the state file
  is missing, also exits 0 (fail-closed — treat as post-merge when probe fails). The
  key is written by `ship-pr.sh` in `run_ci_phase` at the moment a merge succeeds.
- **No push**: commits with `--` pathspec limited to `larch-logs/implement/<RUN_ID>/`;
  the caller (`ship-pr.sh`) owns the subsequent push.
- **Best-effort renders**: `token-report.sh`, `timing-report.sh`, and `larch-log.sh write`
  calls use `|| true`; render failures are non-fatal.
- **`NO_LOGS_COMMIT` honoured**: reads the flag from the state file; skips the commit
  when `true` (mirrors `ship-pr.sh`'s pre-rebase larch-log flush behaviour).

## Primary callers

`scripts/ship-pr.sh` at three trigger points (all inside pre-push code paths):

- **Trigger A** (`run_rebase_rebump`): after re-bump, before `git-force-push.sh`.
- **Trigger B** (`run_ci_fix_vendor`): after fix commit, before `git-push.sh`.
- **Trigger C** (`run_bump_phase`): after bump block, before `write_postbump_state`.

## Harness

`scripts/test-refresh-run-logs.sh` — covers happy-path commit, post-merge skip,
and probe-failure fail-closed cases. Run via `make test-refresh-run-logs`.

## Edit-in-sync

Any change to the stdout contract or `--state-file` / `MERGE_RESULT` semantics must
be reflected in `scripts/ship-pr.md` and `scripts/test-refresh-run-logs.sh`.
