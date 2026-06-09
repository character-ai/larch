# plan-review-loop.sh

**Consumer**: `/design` Step 3 — single-pass plan-review driver.

**Primary callers**: `skills/design/scripts/run-step3-review.sh` (invoked from `skills/design/SKILL.md` Step 3).

External plan-review launches are transitively covered by the launch-time
health gate in `scripts/run-external-agent.sh`: the Step 3 review launcher
family funnels Codex/Cursor commands through that chokepoint, so this driver
does not own a separate `check-reviewers.sh` probe or timeout knob.

## Invariants

Validates `$DESIGN_TMPDIR` via `larch_design_tmpdir_validate` after the required-arg check, before resolving the path with `cd ... && pwd -P`.

- Writes session-root artifacts under `$DESIGN_TMPDIR/`: `ballot.txt`, `accepted-plan-findings.md`, `accepted-plan-findings-all.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md`. `ballot.txt` is created or truncated on every exit path (including `panel-failed` and zero-finding short-circuit) so consumers avoid `ENOENT`. Never revises `plan.txt`; Gate B is the only apply point.
- `accepted-plan-findings-all.md` is cumulative for automatic Step 3 continuation rounds before Gate C; Gate B still reads only `accepted-plan-findings.md`. `main-agent-vote-required` does not merge tentative accepted findings until the MainAgent re-tally succeeds.
- `oos-accepted-design.md` is cumulative for the current Step 3 run. Zero-finding, tally-error, and panel-failed branches preserve the prior cumulative file instead of truncating it, and only accepted OOS blocks are merged forward.
- Honors `LARCH_AGGREGATOR_DISABLED=1` by skipping `aggregate-findings.sh` and setting `AGGREGATOR_STATUS=disabled`.
- Emits stdout KV lines documented below plus optional `WARN=` lines. `WARN=plan-review-tsv: empty or missing structured reviewer rows for …` is suppressed when the reviewer output file contains the canonical `{"no_issues_found": true}` zero-findings sentinel (healthy slot with no TSV rows); the warning still fires for genuinely empty or unparseable output (header-only TSV with no sentinel).
- **Per-slot drop diagnostics (#3392).** When the panel forwards `DROPPED_SLOTS_FILE` (the `--no-fallback` drop sidecar from `dispatch-with-waterfall.sh`), `_log_dropped_slots` appends one entry per dropped reviewer slot to `$DESIGN_TMPDIR/execution-issues.md` under **External Reviewer Issues** (via `scripts/append-tool-failure.sh --redact`), tagged with the drop reason (`format-gate-miss`, `collector-failure`, `tool-absent`, `empty`, `result-gate-miss`, `result-unreadable`) and a snippet of the offending output. This fires for partial drops (some slots kept) as well as total drops, so a healthy reviewer dropped only for leading with a preamble is no longer invisible. When the round produces no reviewer paths at all, the aggregate `WARN=plan-review-panel: dispatch produced no reviewer paths …` names the dropped-slot count and points at the per-slot records.
- Writes `$DESIGN_TMPDIR/plan-review/round-<N>/findings-classification.tsv` for normal tally runs; header-only TSV on empty-artifact exits.
- Writes `$DESIGN_TMPDIR/.step3-plan-review-result.env` at every terminal exit.
- Per-round forensics allowlist: `scripts/lib-design-round-artifacts.md`.
- Allowed snapshot inputs must be regular files. If an allowlisted session-root artifact resolves as a symlink, the new snapshot payload is discarded and terminal statuses keep their original `LOOP_STATUS` while appending `snapshot-failed` to `REASON` when the failure happens after a terminal outcome has already been determined.

## Argv

`--design-tmpdir`, `--plan-file`, optional `--feature-file`, `--round-num` (round label; default 1), `--codex-present`, `--cursor-present`, optional `--timeout` (default 1860), `--help`. The per-round scout invocation (`$PLAN_REVIEW_SCOUT_SH`, default `scout-plan-archetypes-wrapper.sh`) receives the same `--codex-present` / `--cursor-present` values.

The script always runs one pass and never invokes the revision waterfall; Gate B is the apply point.

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
| `SCOPE_ANCHOR_FILE` | Dual gate: `TALLY_PLAN_REVIEW_STATUS` in (`ok`, `main-agent-vote-required`) and `LOOP_STATUS` in (`complete`, `main-agent-vote-required`); path to staged binding issue scope anchor |
| `NIT_ACCEPTED_COUNT` | Single-pass severity count |
| `NON_NIT_ACCEPTED_COUNT` | Single-pass severity count |
| `REASON` | When annotated (`zero-findings`, `zero-findings-degraded-panel`, etc.) |
| `REVISE_STATUS` | Always `skipped` in single-pass mode |
| `COLLECT_OK_COUNT` / `COLLECT_FAILURE_COUNT` | Collector evidence counts |

`LOOP_STATUS` values: `complete`, `zero-findings-degraded-panel`, `tally-error`, `degraded-empty-collector`, `panel-failed`, `main-agent-vote-required`.

## Single-pass status mapping

The driver runs one review round and never revises `plan.txt`. It counts collector evidence before terminal mapping, preserves `panel-failed`, preserves `main-agent-vote-required`, preserves `tally-error`, accumulates accepted OOS findings, then maps zero accepted / zero collectors to `degraded-empty-collector`, zero accepted / degraded panel to `zero-findings-degraded-panel`, and all remaining successful outcomes to `complete`. Tally-error restores cumulative accepted artifacts and clears the current accepted artifact before exit. Normative narrative: `skills/design/references/plan-review.md` § Single-pass review.

## Durable handoff: `.step3-plan-review-result.env`

Normalized KVs for SKILL.md Step 3.5 and Gate B across Bash fence boundaries. Values use a controlled vocabulary (no raw user content) except `SCOPE_ANCHOR_FILE`, which is a path handoff to the staged binding issue scope anchor. The loop strips any raw `SCOPE_ANCHOR_FILE=` lines from tally stdout before relay, then re-emits/persists the normalized key only when both tally and loop terminals pass the dual gate (`TALLY_PLAN_REVIEW_STATUS` in `ok`/`main-agent-vote-required` and `LOOP_STATUS` in `complete`/`main-agent-vote-required`); a parsed tally KV wins, otherwise the materialized loop input path is used when the tally omitted the key. `tally-error`, `panel-failed`, and other non-terminal paths omit the key. `round-summary.env` uses the same gate. See `plan-review-loop.sh` functions `_scope_anchor_handoff_value` and `write_step3_result_env`.

## `round-summary.env` schema

Written under `plan-review/round-N/round-summary.env` after each round's outcome is known. Keys: `ROUND_NUM`, `LOOP_STATUS` (terminal rounds only), `REASON`, `NIT_ACCEPTED_COUNT`, `NON_NIT_ACCEPTED_COUNT`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `TALLY_PLAN_REVIEW_STATUS`, `AGGREGATOR_STATUS`, `REVISE_STATUS`, `COLLECT_OK_COUNT`, `COLLECT_FAILURE_COUNT`, `SCOPE_ANCHOR_FILE`. `REVISE_STATUS` is `skipped` because single-pass Step 3 never applies findings. `REVISE_WINNING_TIER` was removed after the revise waterfall was dropped from Step 3.

## Exit codes

| Code | `LOOP_STATUS` |
|------|----------------|
| 0 | `zero-findings-degraded-panel`, `main-agent-vote-required`, `complete`, `tally-error`, `degraded-empty-collector` |
| 1 | `panel-failed` |
| 2 | argv error |

## Plan-size handling

Step 3 no longer runs a loop-internal post-apply pipeline, so plan-size and validator handoffs occur only at Gate B / discussion merged fences or retained Step 2b.5 callers.

## Cross-links

- `scripts/lib-design-round-artifacts.md` — snapshot/publish allowlist
- `aggregate-findings.md` — `--allow-findings-outside-tmpdir true`
- `tally-plan-review.md`, `dispatch-plan-voters.md`

## Cross-entry forensics

`run-step3-review.sh` clears only the active `plan-review/round-<N>/` slot before launch. Earlier automatic continuation rounds remain in place for diagnostics and cumulative summaries; a later manual Gate C re-run may overwrite the active round slot it is about to produce.

## Makefile

`make test-plan-review-loop` — see `skills/design/scripts/test-plan-review-loop.sh`.

`make test-design-multi-round-integration` — cross-script per-entry/log-publish and automatic continuation harness.

## Edit-in-sync

Keep this file aligned with `plan-review-loop.sh` behavior and argv.

Single-pass mode records one best-effort design plan-review timing `round` row per terminal exit through `_snapshot_terminal_exit_preserving_status`. `main-agent-vote-required` persists `round-start-s` under `plan-review/round-N/` and defers emission to `skills/design/SKILL.md` after inline re-tally.

## Scope anchor and scope-reduction preservation

Each plan-review run materializes `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` from the originating feature text after `scripts/plan-block-strip-body.sh` removes any prior `larch:plan` block. An approved `design-outline.md` is appended only when `.outline-approved` exists. Post-redaction empty anchors fail materialization with exit code 2. Anchors above 64KiB fail materialization with exit code 2 (no `LOOP_STATUS`; argv/config failure before the review round starts). Brainstorm synthesis is written to `plan-review-feature-context.txt` as optional non-binding context and is not used as the binding scout/reviewer/voter/MainAgent fallback anchor. The loop emits `SCOPE_ANCHOR_FILE` through `emit_loop_kvs`, the terminal machine-output KV stream, and `.step3-plan-review-result.env` only after the normalized tally gate described above.

Collected in-scope findings are snapshotted to `findings-in-scope.pre-dedup.md` before Jaccard dedup. Dedup uses the canonical scope-reduction marker detector, strips severity and `[SCOPE-REDUCTION]` only for comparison, preserves tagged bodies when merging with untagged duplicates, and falls back to the pre-dedup in-scope snapshot if post-dedup tagged parity fails. For scope-reduction-tagged blocks, Jaccard comparison text prefers **Concern** / **Description** body text over the `### FINDING_N:` header alone so divergent headers with distinct concerns are not merged; dedup and parity helpers share the same `problem_text()` extraction. Ballot input is sequentially renumbered for `FINDING_*` and `OOS_*` headings after aggregation or fallback. `AGGREGATED=false` keeps the current in-scope stream rather than restoring pre-split files. No baseline plan file is created.

## Conditional reviewer pruning

`--prune-round-num` is optional: when omitted, it defaults to `--round-num` without reading `$DESIGN_TMPDIR/review-round-count.txt`. `run-step3-review.sh` passes the review-round counter explicitly, keeping that launcher the sole writer/reader of the durable count contract while direct single-pass callers remain stateless. `--round-num` remains the artifact directory index. The loop forwards `--prune-ledger "$DESIGN_TMPDIR/reviewer-prune-ledger.tsv"` to `dispatch-plan-review-panel.sh`, parses `PANEL_PRUNED_EMPTY`, and uses the canonical post-filter `plan-review-slots.ndjson` for output-to-slot mapping and `Cursor-Arch`-style label-map generation. A pruned-empty panel exits through `_snapshot_terminal_exit_preserving_status` as complete/non-degraded without recording ledger rows, after restoring cumulative OOS state. Healthy zero-findings rounds create a header-only findings-classification TSV, record zero accepted counts for launched slots, restore cumulative OOS state, and exit through the same terminal snapshot path. Normal settled tallies record via `reviewer-prune.sh`; panel-failed, tally-error, main-agent-vote-required, and pruned-empty paths do not record.
