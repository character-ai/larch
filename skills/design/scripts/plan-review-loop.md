# plan-review-loop.sh

**Consumer**: `/design` Step 3 — multi-round plan-review driver (legacy single-pass when `--round-cap` is omitted on argv).

**Primary callers**: `skills/design/scripts/run-step3-review.sh` (invoked from `skills/design/SKILL.md` Step 3).

External plan-review launches are transitively covered by the launch-time
health gate in `scripts/run-external-agent.sh`: the Step 3 review launcher
family funnels Codex/Cursor commands through that chokepoint, so this driver
does not own a separate `check-reviewers.sh` probe or timeout knob.

## Invariants

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before resolving the path with `cd ... && pwd -P`.

- Writes session-root artifacts under `$DESIGN_TMPDIR/`: `ballot.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md`. `ballot.txt` is created or truncated on every exit path (including `panel-failed` and zero-finding short-circuit) so consumers avoid `ENOENT`. Never revises `plan.txt` in legacy mode; multi-round mode auto-applies via `revise-plan-with-waterfall.sh` when `manual_gate_b=false`.
- In multi-round mode, `oos-accepted-design.md` is cumulative across settled rounds. Zero-finding, tally-error, and panel-failed branches preserve the prior cumulative file instead of truncating it, and only accepted OOS blocks are merged forward.
- Honors `LARCH_AGGREGATOR_DISABLED=1` by skipping `aggregate-findings.sh` and setting `AGGREGATOR_STATUS=disabled`.
- Emits stdout KV lines documented below plus optional `WARN=` lines. `WARN=plan-review-tsv: empty or missing structured reviewer rows for …` is suppressed when the reviewer output file contains the canonical `{"no_issues_found": true}` zero-findings sentinel (healthy slot with no TSV rows); the warning still fires for genuinely empty or unparseable output (header-only TSV with no sentinel).
- **Per-slot drop diagnostics (#3392).** When the panel forwards `DROPPED_SLOTS_FILE` (the `--no-fallback` drop sidecar from `dispatch-with-waterfall.sh`), `_log_dropped_slots` appends one entry per dropped reviewer slot to `$DESIGN_TMPDIR/execution-issues.md` under **External Reviewer Issues** (via `scripts/append-tool-failure.sh --redact`), tagged with the drop reason (`format-gate-miss`, `collector-failure`, `tool-absent`, `empty`, `result-gate-miss`, `result-unreadable`) and a snippet of the offending output. This fires for partial drops (some slots kept) as well as total drops, so a healthy reviewer dropped only for leading with a preamble is no longer invisible. When the round produces no reviewer paths at all, the aggregate `WARN=plan-review-panel: dispatch produced no reviewer paths …` names the dropped-slot count and points at the per-slot records.
- Writes `$DESIGN_TMPDIR/plan-review/round-<N>/findings-classification.tsv` for normal tally runs; header-only TSV on empty-artifact exits.
- Writes `$DESIGN_TMPDIR/.step3-plan-review-result.env` at every terminal exit (multi-round and legacy).
- Per-round forensics allowlist: `scripts/lib-design-round-artifacts.md`.
- Allowed snapshot inputs must be regular files. If an allowlisted session-root artifact resolves as a symlink, the new snapshot payload is discarded, pre-existing `round-N/revise/` forensics are preserved, and terminal statuses keep their original `LOOP_STATUS` while appending `snapshot-failed` to `REASON` when the failure happens after a terminal outcome has already been determined.

## Argv

`--design-tmpdir`, `--plan-file`, optional `--feature-file`, `--round-num` (starting round; default 1), optional `--round-cap N` (enables multi-round when present on argv; default value from `LARCH_DESIGN_ROUND_CAP` only applies when the flag is passed), `--codex-present`, `--cursor-present`, optional `--timeout` (default 1860), `--help`. The per-round scout invocation (`$PLAN_REVIEW_SCOUT_SH`, default `scout-plan-archetypes-wrapper.sh`) receives the same `--codex-present` / `--cursor-present` values.

**Legacy contract**: omit `--round-cap` → single pass, `LOOP_STATUS=complete`, no inner revise loop.

## Machine output (stdout)

| Key | When set |
|-----|----------|
| `LOOP_STATUS` | Always |
| `ACCEPTED_COUNT` | Always |
| `IMPORTANT_ACCEPTED_COUNT` | Always |
| `DEGRADED_PANEL` | Always |
| `ROUNDS_COMPLETED` | Always |
| `AGGREGATOR_STATUS` | Always |
| `TALLY_PLAN_REVIEW_STATUS` | Always |
| `VOTING_TALLY_FILE` | Always |
| `VOTER_1_PARSE_RATE_STATUS` | Always |
| `SCOPE_ANCHOR_FILE` | Always; path to staged binding issue scope anchor |
| `NIT_ACCEPTED_COUNT` | Multi-round |
| `NON_NIT_ACCEPTED_COUNT` | Multi-round |
| `REASON` | When annotated (`zero-findings`, `zero-findings-degraded-panel`, `converged`, `cap-hit`, `revision-failed`, `manual-gate-b`, etc.) |
| `REVISE_STATUS` | Multi-round revise path |
| `COLLECT_OK_COUNT` / `COLLECT_FAILURE_COUNT` | Multi-round |

`LOOP_STATUS` values: `complete`, `converged`, `cap-hit`, `zero-findings-degraded-panel`, `revision-failed`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `emit-plan-failed`, `panel-failed`, `main-agent-vote-required`.

`plan-size-trigger` is a breadcrumb from an auto-revised round, not the hard prompt itself. The caller must re-run the complete Step 2b.5 plan-size procedure before prompting so `check-plan-size.sh` refreshes the current trigger KVs, then honor the hard prompt's **Split / Override / Cancel** contract: Split enters Split-path, Override records the strongly discouraged escape hatch and continues the surrounding review flow, and Cancel exits.

## Convergence (multi-round)

When `--round-cap` is present on argv, the driver may exit `LOOP_STATUS=converged` after **one** non-degraded qualifying round — there is no multi-round streak. Convergence requires non-nit `ACCEPTED_COUNT <= 5`, `IMPORTANT_ACCEPTED_COUNT == 0`, and nit-severity accepted findings excluded from the non-nit total (`NIT_ACCEPTED_COUNT` / `NON_NIT_ACCEPTED_COUNT` on stdout). Zero-findings rounds additionally require `COLLECT_OK_COUNT > 0`; otherwise `LOOP_STATUS=degraded-empty-collector`. `TALLY_PLAN_REVIEW_STATUS=tally-error` aborts before revise/convergence checks. Normative narrative: `skills/design/references/plan-review.md` § Multi-round loop.

## Durable handoff: `.step3-plan-review-result.env`

Normalized KVs for SKILL.md Step 3.5 and Gate B across Bash fence boundaries. Values use a controlled vocabulary (no raw user content) except `SCOPE_ANCHOR_FILE`, which is a validated path handoff to the staged binding issue scope anchor. See `plan-review-loop.sh` function `write_step3_result_env`.

## `round-summary.env` schema

Written under `plan-review/round-N/round-summary.env` after each round's outcome is known. Keys: `ROUND_NUM`, `LOOP_STATUS` (terminal rounds only), `REASON`, `NIT_ACCEPTED_COUNT`, `NON_NIT_ACCEPTED_COUNT`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `TALLY_PLAN_REVIEW_STATUS`, `AGGREGATOR_STATUS`, `REVISE_STATUS`, `REVISE_WINNING_TIER`, `PLAN_HASH_BEFORE_REVISE`, `PLAN_HASH_AFTER_REVISE`, `COLLECT_OK_COUNT`, `COLLECT_FAILURE_COUNT`, `SCOPE_ANCHOR_FILE`. Successful tier-4 fallback rounds preserve `REVISE_STATUS=ok-fallback` here instead of being normalized to `ok`.

## Exit codes

| Code | `LOOP_STATUS` |
|------|----------------|
| 0 | `converged`, `cap-hit`, `zero-findings-degraded-panel`, `revision-failed`, `main-agent-vote-required`, `complete`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `emit-plan-failed` |
| 1 | `panel-failed` |
| 2 | argv error |

## `check-plan-size.sh` call in `_run_post_apply_pipeline`

The post-apply pipeline calls `check-plan-size.sh` to check the revised plan size. Behavior:

- **rc 2/3 (nonfatal)**: captures stdout to `check-plan-size.validation.log`; appends a `Warnings` entry to `execution-issues.md` via `append-tool-failure.sh` with `>/dev/null 2>&1 || true` so helper KVs such as `APPENDED=` / `LOG=` never reach loop stdout; emits a display `⚠` line; treats the plan as under-threshold and returns clean (partition handoff suppressed when rc=0 check was skipped this way).
- **rc 0 + `partition_requested=true`** (from `run-params.json`, parsed with `jq` when available, bare sed-based boolean fallback otherwise): emits `LOOP_STATUS=plan-size-trigger` with `REASON=plan-size-partition`. Caller must use the retained **Split / Override / Cancel** hard-prompt contract for plan-review-loop sites.
- **rc 0 + hard trigger**: emits `LOOP_STATUS=plan-size-trigger` as before.
- **Hard wins over partition** when both fire on the same plan.

`CHECK_PLAN_SIZE_SH` resolves as `${LARCH_CHECK_PLAN_SIZE_SH:-${CHECK_PLAN_SIZE_SH:-$PLUGIN_ROOT/.../check-plan-size.sh}}`, exposing a test-override env var.

## Cross-links

- `scripts/lib-design-round-artifacts.md` — snapshot/publish allowlist
- `revise-plan-with-waterfall.md` — `REVISE_STATUS` contract
- `aggregate-findings.md` — `--allow-findings-outside-tmpdir true`
- `tally-plan-review.md`, `dispatch-plan-voters.md`

## Cross-entry forensic limitation

Each Step 3 entry clears `plan-review/round-*/` before launch (SKILL.md); prior Step 3 entry forensics are not retained across Gate C re-runs.

## Makefile

`make test-plan-review-loop` — see `skills/design/scripts/test-plan-review-loop.sh`.

`make test-design-multi-round-integration` — cross-script harness.

## Edit-in-sync

Keep this file aligned with `plan-review-loop.sh` behavior and argv.

Multi-round mode records one best-effort design plan-review timing `round` row per completed round. Terminal exits emit through `_snapshot_terminal_exit_preserving_status`; `main-agent-vote-required` persists `round-start-s` under `plan-review/round-N/` and defers emission to `skills/design/SKILL.md` after inline re-tally.

## Scope anchor and scope-reduction preservation

Each plan-review run materializes `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` from the originating feature text after `scripts/plan-block-strip-body.sh` removes any prior `larch:plan` block. An approved `design-outline.md` is appended only when `.outline-approved` exists. Brainstorm synthesis is written to `plan-review-feature-context.txt` as optional non-binding context and is not used as the binding scout/reviewer/voter/revise anchor. The loop emits `SCOPE_ANCHOR_FILE` through `emit_loop_kvs`, the terminal machine-output KV stream, and `.step3-plan-review-result.env` for durable Step 3 handoff.

Collected in-scope findings are snapshotted to `findings-in-scope.pre-dedup.md` before Jaccard dedup. Dedup uses the canonical scope-reduction marker detector, strips severity and `[SCOPE-REDUCTION]` only for comparison, preserves tagged bodies when merging with untagged duplicates, and falls back to the pre-dedup in-scope snapshot if post-dedup tagged parity fails. Ballot input is sequentially renumbered for `FINDING_*` and `OOS_*` headings after aggregation or fallback. `AGGREGATED=false` keeps the current in-scope stream rather than restoring pre-split files. No baseline plan file is created.
