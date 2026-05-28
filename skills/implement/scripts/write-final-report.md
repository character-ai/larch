# write-final-report.sh (`/implement`)

Builds the **rich markdown** final run summary, writes the committed `final-summary.md` (unless `--comment-only`), upserts the tracking-issue `larch:final-summary` comment, and optionally mirrors the body to the renderer print stream via `--print-stdout`. Top-chat visibility is owned by the `/implement` orchestrator, which emits the persisted `summary-final.md` body verbatim after the Bash call per `skills/implement/SKILL.md`.

The markdown body is produced by [`scripts/render-run-summary.sh`](../../../scripts/render-run-summary.md): a `## /<skill> run <run-id> — <outcome>` heading, the normalized bullet list, then the `<!-- larch:run-summary v=1 -->` sentinel (see that script’s contract). The renderer emits `- **Outcome**:` for outcomes matching `bailed*`, `stalled`, `cancelled-*`, or `failed-*`, emits `- Emergency: true` when `run-flags.sh` has `EMERGENCY_REQUESTED=true`, and omits `- **PR**:` when the normalized display would be `N/A`. Optional per-lane USD lines use [`scripts/token-cost.sh`](../../../scripts/token-cost.sh) and the env vars documented under **Per-vendor rates** in [`docs/configuration-and-permissions.md`](../../../docs/configuration-and-permissions.md).

## Implement outcome enum (`**Outcome**:` / `--outcome` display)

These nine values are the complete set emitted for `/implement` runs (computed in `write-final-report.sh` from `ship-pr-state.sh`, `finalize-state.sh`, and related inputs). The harness `test-write-final-report.sh` is expected to stay aligned with this list.

1. `stalled` — `STALL_TRACKING=true` in ship-pr state (or finalize state when ship-pr left it false).
2. `forked-dry-run` — `FORKED_TARGET=true`.
3. `design-only` — `DESIGN_ONLY_DONE=true`.
4. `merged` — `MERGE_RESULT` is `merged` or `admin_merged`.
5. `force-merged-externally` — `MERGE_RESULT=already_merged`.
6. `pr-created-draft` — non-zero `PR_NUMBER` and `DRAFT=true`.
7. `pr-created` — non-zero `PR_NUMBER`, `DRAFT=false`, `MERGE=false`.
8. `bailed` — none of the above success/partial paths matched; assigned only after the explicit if/elif chain as a fallthrough default.
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
| `run-flags.sh` | `NO_ISSUES`, `WORKFLOW_PATH`, `EMERGENCY_REQUESTED` (from `persist-implement-run-flags.sh`); legacy `QUICK_MODE` line may exist but is ignored |
| `larch-logs/implement/<RUN_ID>/` | `token-report.json`, `timing-report.json`, review tallies, OOS / execution-issues batches |

## Outputs

| Artifact | When |
|----------|------|
| `$IMPLEMENT_TMPDIR/summary-final.md` | Always (upsert payload) |
| `larch-logs/implement/<RUN_ID>/final-summary.md` | Unless `--comment-only` |
| KV lines | Always (see below) |

### `--print-stdout`

When set, the script exports `PRINT_STDOUT=true` and prints the rendered markdown body to FD **3** when `lib-quiet.sh` owns the session (`LARCH_QUIET_PID=$$`), else to **stdout**. Status KV lines go to FD **4** (quiet session) or **stderr** (non-quiet), via `emit_kv_out`. This is the renderer's print mechanism; top-chat visibility is achieved by the orchestrator emitting the persisted `$IMPLEMENT_TMPDIR/summary-final.md` body verbatim after the Bash call (per `skills/implement/SKILL.md` Step 17 / Step 18 prose). The FD-3-vs-stdout choice remains relevant for lib-quiet-aware callers, but it is not the primary top-chat visibility channel. The canonical tmpdir basename is `summary-final.md`, distinct from the committed `larch-logs/implement/<RUN_ID>/final-summary.md` run-log artifact.

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

## Token-data-missing primary path

When no usable token JSON exists, or the JSON is unparseable / lacks
`.claude.totals`, the primary `render-run-summary.sh` call passes
`--cost-unavailable` and omits token count flags. The rendered body therefore
uses `- **Cost**: N/A` instead of the misleading all-zero dollar line.

When `token-report.json` contains structurally present multi-vendor sections
whose reported totals are all zero, the script treats the report as corrupt
token data. Claude-only all-zero reports are exempt from that corrupt-data
warning path as a legitimate single-agent/no-usage case, but still render
`- **Cost**: N/A` because there is no positive token usage data. The
corrupt-data path keeps the same
`- **Cost**: N/A` rendering path, appends
`**⚠ token-report.json appears corrupt; reporting Cost: N/A**` to the rendered
summary body, and repeats that warning on stderr for operators.

## Degraded render — two-stage fallback

If `render-run-summary.sh` fails or produces an empty file, the script appends a
Warning to `execution-issues.md`, refreshes warning counts, and re-invokes the
renderer with `--cost-unavailable`. That Stage 1 fallback preserves the full
renderer schema while forcing `- **Cost**: N/A`.

If Stage 1 also fails, Stage 2 writes a self-composed markdown body that mirrors
the renderer's `/implement` schema: conditional `- **Outcome**:` only for
`bailed*` / `stalled` / `cancelled-*` / `failed-*`, conditional `- **PR**:` only
when a PR display exists, always includes `- **Code review**:`, always includes
`- **Cost**: N/A`, and ends with `<!-- larch:run-summary v=1 -->`. The body still
surfaces through `--print-stdout`.

Only this terminal self-composed fallback is marked as degraded. It places
`**⚠ Degraded fallback — full renderer failed; warning recorded in execution
issues.**` immediately after the `## /implement run ...` heading, with one
blank line on each side, and emits
`<!-- larch:final-summary-fallback v1 -->` directly after the existing
`<!-- larch:run-summary v=1 -->` marker. The heading remains the first
non-empty line for first-line outcome parsers. Exit code behavior is unchanged:
the fallback still exits 0 after recording Warnings in `execution-issues.md`
(published as `execution-issues.ndjson` in run logs).

The Stage 1 `--cost-unavailable` retry is a real renderer body and must not
carry the degraded-fallback banner or marker; the harness regression-guards
that distinction.
