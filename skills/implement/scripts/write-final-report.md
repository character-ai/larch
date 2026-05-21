# write-final-report.sh (`/implement`)

Builds the **rich markdown** final run summary, writes the committed `final-summary.md` (unless `--comment-only`), upserts the tracking-issue `larch:final-summary` comment, and optionally mirrors the body to chat via `--print-stdout`.

The markdown body is produced by [`scripts/render-run-summary.sh`](../../../scripts/render-run-summary.md): a `## /<skill> run <run-id> — <outcome>` heading, the normalized bullet list, then the `<!-- larch:run-summary v=1 -->` sentinel (see that script’s contract). Optional per-lane USD lines use [`scripts/token-cost.sh`](../../../scripts/token-cost.sh) and the env vars documented under **Per-vendor rates** in [`docs/configuration-and-permissions.md`](../../../docs/configuration-and-permissions.md).

## Implement outcome enum (`**Outcome**:` / `--outcome` display)

These nine values are the complete set emitted for `/implement` runs (computed in `write-final-report.sh` from `ship-pr-state.sh`, `finalize-state.sh`, and related inputs). The harness `test-write-final-report.sh` is expected to stay aligned with this list.

1. `stalled` — `STALL_TRACKING=true` in ship-pr state (or finalize state when ship-pr left it false).
2. `forked-dry-run` — `FORKED_TARGET=true`.
3. `design-only` — `DESIGN_ONLY_DONE=true`.
4. `merged` — `MERGE_RESULT` is `merged` or `admin_merged`.
5. `force-merged-externally` — `MERGE_RESULT=already_merged`.
6. `pr-created-draft` — non-zero `PR_NUMBER` and `DRAFT=true`.
7. `pr-created` — non-zero `PR_NUMBER`, `DRAFT=false`, `MERGE=false`.
8. `bailed` — none of the above success/partial paths matched (default).
9. `bailed-needs-user-input` — `BAIL_NEEDS_USER_INPUT=true` on finalize state **and** the outcome would otherwise be `bailed` (distinct bail class for operator follow-up).

## Usage

```bash
write-final-report.sh --implement-tmpdir PATH [--comment-only] [--print-stdout]
```

## Inputs (files under `IMPLEMENT_TMPDIR`)

| File | Keys / role |
|------|----------------|
| `parent-issue.md` | `ISSUE_NUMBER`, `RUN_ID`, optional `ISSUE_URL` |
| `session-env.sh` | `REPO`, `REPO_UNAVAILABLE`, `UPSTREAM_DESIGN_ISSUE`, `POST_PLAN_WORKFLOW_PATH` (fallback) |
| `ship-pr-state.sh` | `PR_URL`, `PR_NUMBER`, `STALL_TRACKING`, `MERGE_RESULT`, `MERGE`, `DRAFT`, `FORKED_TARGET` |
| `finalize-state.sh` | `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, optional `STALL_TRACKING` |
| `run-flags.sh` | `NO_ISSUES`, `WORKFLOW_PATH` (from `persist-implement-run-flags.sh`); legacy `QUICK_MODE` line may exist but is ignored |
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

## `RUN_ID` validation

After resolving `RUN_ID` from `parent-issue.md` or `session-id`, the script rejects values that contain `/` or `..` using the same **character-class rejection** as `scripts/refresh-run-logs.sh` (`*/*` / `*'..'*)`; treat `refresh-run-logs.sh` as a pattern reference only. Here, a rejected `RUN_ID` fails closed: it emits `COMMENT_URL=` (empty), `STATUS=failed`, and `ERROR="invalid RUN_ID (path-traversal characters rejected)"`, and exits non-zero without creating or modifying anything under the run log directory tree (`larch-logs/implement/<RUN_ID>/`). By contrast, `refresh-run-logs.sh` treats invalid `RUN_ID` as a non-fatal skip (`REFRESH_SKIPPED=true`, `REASON=invalid-run-id`) and exits `0`.

## `--comment-only`

Still refreshes `summary-final.md` for the upsert but **does not** overwrite `larch-logs/.../final-summary.md`. Used by `ship-pr.sh` after PR creation so the tracking comment picks up the live URL without dirtying the run-log tree before the next flush.

## Degraded render

If `render-run-summary.sh` fails or produces an empty file, the script falls back to a minimal markdown stub that still includes the `<!-- larch:run-summary v=1 -->` sentinel.
