# write-final-report.sh (`/implement`)

Builds the **rich markdown** final run summary, writes the committed `final-summary.md` (unless `--comment-only`), upserts the tracking-issue `larch:final-summary` comment, and optionally mirrors the body to chat via `--print-stdout`.

The markdown body is produced by [`scripts/render-run-summary.sh`](../../../scripts/render-run-summary.md) (starts with `<!-- larch:run-summary v=1 -->`). Optional per-lane USD lines use [`scripts/token-cost.sh`](../../../scripts/token-cost.sh) and the env vars documented under **Per-vendor rates** in [`docs/configuration-and-permissions.md`](../../../docs/configuration-and-permissions.md).

## Usage

```bash
write-final-report.sh --implement-tmpdir PATH [--comment-only] [--print-stdout]
```

## Inputs (files under `IMPLEMENT_TMPDIR`)

| File | Keys / role |
|------|----------------|
| `parent-issue.md` | `ISSUE_NUMBER`, `RUN_ID`, optional `ISSUE_URL` |
| `session-env.sh` | `REPO`, `REPO_UNAVAILABLE`, `AUTO_MODE`, `UPSTREAM_DESIGN_ISSUE`, `POST_PLAN_WORKFLOW_PATH` (fallback) |
| `ship-pr-state.sh` | `PR_URL`, `PR_NUMBER`, `STALL_TRACKING`, `MERGE_RESULT`, `MERGE`, `DRAFT`, `FORKED_TARGET` |
| `finalize-state.sh` | `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, optional `STALL_TRACKING` |
| `run-flags.sh` | `QUICK_MODE`, `NO_ISSUES`, `WORKFLOW_PATH` (from `persist-implement-run-flags.sh`) |
| `larch-logs/implement/<RUN_ID>/` | `token-report.json`, `timing-report.json`, review tallies, OOS / execution-issues batches |

## Outputs

| Artifact | When |
|----------|------|
| `$IMPLEMENT_TMPDIR/summary-final.md` | Always (upsert payload) |
| `larch-logs/implement/<RUN_ID>/final-summary.md` | Unless `--comment-only` |
| KV lines | Always (see below) |

### `--print-stdout`

When set, the script exports `PRINT_STDOUT=true` and prints the rendered markdown body to FD **3** when `lib-quiet.sh` owns the session (`LARCH_QUIET_PID=$$`), else to **stdout**. Status KV lines go to FD **4** (quiet session) or **stderr** (non-quiet), via `emit_kv_out`.

### Key-value contract (`emit` / `emit_kv_out`)

| Key | Values |
|-----|--------|
| `COMMENT_URL` | Upserted comment URL, or empty on skip/failure |
| `STATUS` | `ok` \| `skipped` \| `failed` |
| `REASON` | On `skipped`: `issue-not-set` or `repo-unavailable` |
| `ERROR` | On `failed`: short message |

`STATUS=skipped` when `ISSUE_NUMBER=0` or `REPO_UNAVAILABLE=true`. GitHub upsert failure → `STATUS=failed`, non-zero exit.

## `--comment-only`

Still refreshes `summary-final.md` for the upsert but **does not** overwrite `larch-logs/.../final-summary.md`. Used by `ship-pr.sh` after PR creation so the tracking comment picks up the live URL without dirtying the run-log tree before the next flush.

## Degraded render

If `render-run-summary.sh` fails or produces an empty file, the script falls back to a minimal markdown stub that still includes the `<!-- larch:run-summary v=1 -->` sentinel.
