# write-final-report.sh (`/implement`)

Builds the **rich markdown** final run summary, writes the committed `final-summary.md` (unless `--comment-only`), upserts the tracking-issue `larch:final-summary` comment, and optionally mirrors the body to the renderer print stream via `--print-stdout`. Top-chat visibility is owned by the `/implement` orchestrator, which emits the persisted `summary-final.md` body verbatim after the Bash call per `skills/implement/SKILL.md`.

The markdown body is produced by [`scripts/render-run-summary.sh`](../../../scripts/render-run-summary.md): a `## /<skill> run <run-id> — <outcome>` heading, the normalized bullet list, then the `<!-- larch:run-summary v=1 -->` sentinel (see that script’s contract). The renderer emits `- **Outcome**:` for outcomes matching `bailed*`, `stalled`, `cancelled-*`, or `failed-*`, emits `- Emergency: true` when `run-flags.sh` has `EMERGENCY_REQUESTED=true`, and omits `- **PR**:` when the normalized display would be `N/A`. Optional per-lane USD lines use [`python/report_tokens_cost.py`](../../../python/report_tokens_cost.py) and the env vars documented under **Per-vendor rates** in [`docs/configuration-and-permissions.md`](../../../docs/configuration-and-permissions.md). The cost line includes the spawned-process Claude lane (`Claude (subprocess)` / machine name `claude_sub`, issue #3637): this script reads `.claude_sub.totals.total` and `BUCKETS_claude_sub` from `token-report.json` and forwards `--claude-sub-*` token flags to the renderer.

## Implement outcome enum (`**Outcome**:` / `--outcome` display)

These values are emitted by the shared `stall-recovery-report.sh normalize-outcome` helper. `write-final-report.sh` consumes that helper, and Step 18a.5 uses the same API for escalation-success reporting. The harness `test-write-final-report.sh` is expected to stay aligned with the helper.

1. `stalled` — any observed `STALL_TRACKING=true` in ship-pr state, finalize state, or session env.
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
| `session-env.sh` | `REPO`, `REPO_UNAVAILABLE`, `UPSTREAM_DESIGN_ISSUE` |
| `ship-pr-state.sh` | `PR_URL`, `PR_NUMBER`, `STALL_TRACKING`, `MERGE_RESULT`, `MERGE`, `DRAFT`, `FORKED_TARGET` |
| `finalize-state.sh` | `DESIGN_ONLY_DONE`, `BAIL_NEEDS_USER_INPUT`, optional `STALL_TRACKING` |
| `run-flags.sh` | `NO_ISSUES`, `EMERGENCY_REQUESTED` (from `persist-implement-run-flags.sh`); legacy `QUICK_MODE` line may exist but is ignored |
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

After resolving `RUN_ID` from `parent-issue.md` or `session-id`, the script rejects values that contain `/` or `..` using the same **character-class rejection** as `python/cli.py run-log refresh` (`*/*` / `*'..'*)`; treat `run-log refresh` as a pattern reference only. Here, a rejected `RUN_ID` fails closed: it emits `COMMENT_URL=` (empty), `STATUS=failed`, and `ERROR="invalid RUN_ID (path-traversal characters rejected)"`, and exits non-zero without creating or modifying anything under the run log directory tree (`larch-logs/implement/<RUN_ID>/`). By contrast, `run-log refresh` treats invalid `RUN_ID` as a non-fatal skip (`REFRESH_SKIPPED=true`, `REASON=invalid-run-id`) and exits `0`.

## `--comment-only`

Still refreshes `summary-final.md` for the upsert but **does not** overwrite `larch-logs/.../final-summary.md`. Used by `ship-pr.sh` after PR creation so the tracking comment picks up the live URL without dirtying the run-log tree before the next flush.

## PR line counts

After `REPO` and `PR_NUMBER` resolve, when `REPO_UNAVAILABLE=true` the script
skips `python3 python/cli.py token compute-pr-line-counts` entirely and treats line data as
unavailable. Otherwise it first reuses cached `LINES_*` values from
`ship-pr-state.sh` when they match the current `PR_NUMBER`; on cache miss it
invokes the helper under `set +e`, parses `LINES_STATUS` and the four counter
keys, appends a cache entry to `ship-pr-state.sh` when writable, and never
aborts the report on helper failure. This intentionally avoids repeated live
GitHub file-list calls during `--comment-only` refreshes.

When `LINES_STATUS=ok` and all four counters are non-empty integers, both
`run_body_render` branches forward `--code-added`, `--code-deleted`,
`--logs-added`, and `--logs-deleted` to `render-run-summary.sh` using the
Bash 3.2-safe `${line_args[@]+"${line_args[@]}"}` expansion. Otherwise the
renderer omits those flags and the bullet shows `N/A`.

`compose_self_fallback` emits `- **Lines (PR diff)**: …` for schema parity
(`N/A` when counts are unavailable).

## Review phase detail (per-round, issue #3774)

Before composing the note appendix, the script runs
[`scripts/render-review-phase-detail.sh`](../../../scripts/render-review-phase-detail.md)
with `--rounds-root "$IMPLEMENT_TMPDIR"`,
`--findings-file "$run_dir/review-findings-full.jsonl"`,
`--timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"`, the resolved
`--token-ledger "$IMPLEMENT_TMPDIR/larch-tokens-<hash>.jsonl"` (globbed; omitted
when absent), and `--skill implement`, capturing the rendered **Review Phase
Detail** markdown to a temp file. That file is `cat` into the note block (after
the existing notes), so the section lands in the `--note-lines-file` appendix that
`render-run-summary.sh` emits after the `<!-- larch:run-summary v=1 -->` sentinel.

The section is a per-round table (suggestions made/accepted, OOS proposed/accepted,
time, cost, reviewers launched), a Total row, the top reviewers by suggestions
accepted (`vendor/archetype`), and a failed-reviewer-slot breakdown. The Cost
column is the per-round **vendor** cost (Codex + Cursor + Claude subprocess),
attributed by token-ledger timestamp window and priced via `python/report_tokens_cost.py`; it
excludes main-agent Claude, so it is a distinct datum from (and less than) the
single-source dollar-primary `- **Cost**:` line that `render-run-summary.sh` owns.

The helper is best-effort and renders **nothing** when there were no panel review
rounds (for example `--self-review` runs, where Step 5 does no panel review), so
the note block is unchanged in that case; a render failure is swallowed
(`|| : >"$review_detail_file"`) and never blocks the report. `/design`'s plan
review uses a different data model (no per-round `round-meta.json`), so this
injection is `/implement`-only — see the helper's `.md` for the `/design`
follow-up.

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
