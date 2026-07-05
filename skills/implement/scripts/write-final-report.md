# write-final-report.sh (`/implement`)

**MANDATORY: READ ENTIRE FILE before composing user-facing prose: `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`.**

Builds the **rich markdown** final run summary, writes the committed `final-summary.md` (unless `--comment-only`), upserts the tracking-issue `larch:final-summary` comment, and optionally mirrors the body to the renderer print stream via `--print-stdout`. Top-chat visibility is owned by the `/implement` orchestrator, which emits the persisted `summary-final.md` body verbatim after the Bash call per `skills/implement/SKILL.md`.

The markdown body is produced by [`python/cli.py render run-summary`](../../../python/pr_body.py): a `## /<skill> run <run-id>: <outcome>` heading, the normalized bullet list, then the `<!-- larch:run-summary v=1 -->` sentinel (see that script’s contract). The renderer always emits `- **Outcome**:` as the first bullet. Successful outcomes display as `DONE`, `stalled` displays as `STALLED`, and other outcomes display raw. It no longer emits `- **Mode**:`. It emits `- Force: true` when `run-flags.sh` has `FORCE_REQUESTED=true`, and omits `- **PR**:` when the normalized display would be `N/A`. Optional per-lane USD lines use [`python/larch/report/report_tokens_cost.py`](../../../python/larch/report/report_tokens_cost.py) and the env vars documented under **Per-vendor rates** in [`docs/configuration-and-permissions.md`](../../../docs/configuration-and-permissions.md). The cost line includes the spawned-process Claude lane (`Claude (subprocess)` / machine name `claude_sub`, issue #3637): this script reads `.claude_sub.totals.total` and `BUCKETS_claude_sub` from `token-report.json` and forwards `--claude-sub-*` token flags to the renderer.

## Implement outcome enum (`--outcome` raw values)

These values are emitted by the shared `python/cli.py stall-recovery normalize-outcome` helper. `write-final-report.sh` consumes that helper, and Step 18a.5 uses the same API for escalation-success reporting. The harness `test-write-final-report.sh` is expected to stay aligned with the helper.

1. `stalled`: any observed `STALL_TRACKING=true` in ship-pr state, finalize state, or session env.
2. `forked-dry-run`: `FORKED_TARGET=true`.
3. `design-only`: `DESIGN_ONLY_DONE=true`.
4. `merged`: `MERGE_RESULT` is `merged` or `admin_merged`.
5. `force-merged-externally`: `MERGE_RESULT=already_merged`.
6. `pr-created-draft`: non-zero `PR_NUMBER` and `DRAFT=true`.
7. `pr-created`: non-zero `PR_NUMBER`, `DRAFT=false`, `MERGE=false`.
8. `bailed`: none of the above success/partial paths matched; assigned only after the explicit if/elif chain as a fallthrough default.
9. `bailed-needs-user-input`: `BAIL_NEEDS_USER_INPUT=true` on finalize state **and** the outcome would otherwise be `bailed` (distinct bail class for operator follow-up).

## Bail-time `steps_ran` invariant

If the run ends before Step 9a.1 or before `oos file` succeeds, the committed manifest MUST NOT leave `steps_ran` as an ambiguous empty object for downstream audit tooling. Step 9a.1 completion requires post-checkpoint `run-statistics.md`; explicit `manifest.json` `steps_ran.step9a1=true` is valid only together with that file. `step9a1=true` without `run-statistics.md` is a stale or corrupt marker and must fail audit/verify scans. `oos-issues.ndjson` without `run-statistics.md` is provisional disposition evidence and must not suppress `steps_ran.step9a1=false`.

`python/cli.py final-report write` records explicit `steps_ran.step9a1=false` (and `step8` / `step7a` when their on-disk artifacts are absent) for terminal non-merge outcomes (`bailed`, `stalled`, `design-only`, fork dry-run, PR-created-without-merge, etc.); a non-zero exit from that `run-log manifest` call fails finalization. `python/cli.py run-log verify-completeness` treats missing/null `steps_ran` like `jq '.steps_ran // {}'` for the empty-object bail path, matching `python/cli.py audit-runs scan-run`.

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
| `run-flags.sh` | `NO_ISSUES`, `FORCE_REQUESTED` (from `persist-implement-run-flags.sh`); legacy `QUICK_MODE` line may exist but is ignored |
| `larch-logs/implement/<RUN_ID>/` | `token-report.json`, `timing-report.json`, review tallies, OOS / execution-issues batches |

## Outputs

| Artifact | When |
|----------|------|
| `$IMPLEMENT_TMPDIR/summary-final.md` | Always (upsert payload) |
| `larch-logs/implement/<RUN_ID>/final-summary.md` | Unless `--comment-only` |
| KV lines | Always (see below) |

### `--print-stdout`

When set, the script exports `PRINT_STDOUT=true` and prints the rendered markdown body to FD **3** when FD 3 is available, else to **stdout**. Status KV lines go to FD **4** (quiet session) or **stderr** (non-quiet), via `emit_kv_out`. This is the renderer's print mechanism; top-chat visibility is achieved by the orchestrator emitting the persisted `$IMPLEMENT_TMPDIR/summary-final.md` body verbatim after the Bash call (per `skills/implement/SKILL.md` Step 17 / Step 18 prose). The FD-3-vs-stdout choice is not the primary top-chat visibility channel. The canonical tmpdir basename is `summary-final.md`, distinct from the committed `larch-logs/implement/<RUN_ID>/final-summary.md` run-log artifact.

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

Still refreshes `summary-final.md` for the upsert but **does not** overwrite `larch-logs/.../final-summary.md`. Used by the Python ship driver after PR creation so the tracking comment picks up the live URL without dirtying the run-log tree before the next flush.

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
`--logs-added`, and `--logs-deleted` to `python/cli.py render run-summary` using the
Bash 3.2-safe `${line_args[@]+"${line_args[@]}"}` expansion. Otherwise the
renderer omits those flags and the bullet shows `N/A`.

`compose_self_fallback` emits `- **Lines (PR diff)**: …` for schema parity
(`N/A` when counts are unavailable).

## Review phase detail (per-round, issue #3774)

Before composing the note appendix, the script runs
`python/cli.py progress render-phase-detail`
with `--rounds-root "$run_dir"`,
`--findings-file "$run_dir/review-findings-full.jsonl"`,
`--timing-ledger "$IMPLEMENT_TMPDIR/timing-ledger.tsv"`, the resolved
`--token-ledger "$IMPLEMENT_TMPDIR/larch-tokens-<hash>.jsonl"` (globbed; omitted
when absent), and `--skill implement`, capturing the rendered **Review Phase
Detail** markdown to a temp file. That file is `cat` into the note block (after
the existing notes), so the section lands in the `--note-lines-file` appendix that
`python/cli.py render run-summary` emits after the `<!-- larch:run-summary v=1 -->` sentinel.

The section is a per-round table (suggestions made/accepted, OOS proposed/accepted,
time, cost, reviewers launched), a Total row, optional reviewer timing ASCII
Gantt charts, the top reviewers by suggestions accepted (`vendor/archetype`),
and a failed-reviewer-slot breakdown. Final reports do not pass `--no-gantt`.
Reviewer timing charts are included when timing data is available. The
`--no-gantt` flag is reserved for terminal progress output so live progress stays
plain text.

The Cost column is the per-round **vendor** cost (Codex + Cursor + Claude subprocess),
attributed by token-ledger timestamp window and priced via `python/larch/report/report_tokens_cost.py`.

The helper is best-effort. For a valid selected rounds root with zero completed
rounds (for example `--self-review` runs, where Step 5 does no panel review), it
renders `## Review Phase Detail` plus `No review rounds completed.`. A completed
`round-meta.json` only outside the selected `--rounds-root` is still not counted
as a completed round; the final report shows the no-completed-round message for
that selected valid root. Terminal progress (`python/larch/report/progress_report.py`) skips
the shared renderer when every discovered round dir under the selected root lacks
`round-meta.json`, so in-flight-only reviews do not append
`No review rounds completed.` during live Step 5 or design plan review. A render failure is swallowed
(`|| : >"$review_detail_file"`) and never blocks the report. `/design`'s plan
review uses the same shared renderer through its final summary helper; see the
helper's `.md` for the `/design` contract.

## Token-data-missing primary path

When no usable token JSON exists, the JSON is unparseable, `.claude.totals` is
absent, or every available token bucket is zero, the in-process writer passes
`cost_unavailable` to the renderer. The rendered body therefore uses
`- **Cost**: N/A` instead of a misleading all-zero dollar line.

## Render failure behavior

The wrapper delegates to `python/cli.py final-report write`, which renders the
summary in process via `python/cli.py render run-summary` helpers. There is no
separate Bash self-composed renderer fallback. Tracking-comment failures still
return `STATUS=failed` after writing `summary-final.md`; repo-unavailable runs
skip the tracking upsert and return `STATUS=ok` with an empty `COMMENT_URL`.
