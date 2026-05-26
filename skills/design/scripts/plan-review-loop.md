# plan-review-loop.sh

**Consumer**: `/design` Step 3 (`review_budget=full`) — single-pass plan-review driver.

**Primary callers**: `skills/design/SKILL.md` Step 3 (foreground Bash block).

## Invariants

- Writes session-root artifacts under `$DESIGN_TMPDIR/`: `ballot.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md` (same names and parse contracts as the pre-refactor inline flow). `ballot.txt` is created or truncated on every exit path (including `panel-failed` and zero-finding short-circuit) so consumers avoid `ENOENT`.
- Never revises `plan.txt` (Gate B owns plan revision).
- Honors `LARCH_AGGREGATOR_DISABLED=1` by skipping `aggregate-findings.sh` and setting `AGGREGATOR_STATUS=disabled`.
- Emits stdout key/value lines: `LOOP_STATUS`, `ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `VOTING_TALLY_FILE`, `VOTER_1_PARSE_RATE_STATUS`, plus optional `WARN=` lines. When no in-scope or OOS blocks remain after collection/dedup, tally is not invoked and `TALLY_PLAN_REVIEW_STATUS=skipped-empty-findings` is emitted (distinct from a successful tally’s `ok`). Dedup failure sets `DEGRADED_PANEL=1` and a `WARN=` line while retaining raw findings. Non-zero `tally-plan-review.sh` exit still parses any stdout KVs, then forces `TALLY_PLAN_REVIEW_STATUS=tally-error` so `emit_loop_kvs` always runs. On non-zero tally exit, the loop ensures `voting-tally.md` exists with at least the degraded header (`# Plan Review Voting Tally` plus an abort note carrying `rc=<N>`) so downstream `ACTION=FINALIZE` is robust.
- Writes `$DESIGN_TMPDIR/plan-review/round-<N>/findings-classification.tsv`
  for normal tally runs and writes a header-only TSV on empty-artifact exits
  that bypass tally.

## Argv

`--design-tmpdir`, `--plan-file`, optional `--feature-file`, `--round-num` (default 1), `--codex-present`, `--cursor-present`, optional `--timeout` (panel + collect; default 1860), `--help`.

When `$DESIGN_TMPDIR/brainstorm.md` exists and is non-empty, the driver materializes `$DESIGN_TMPDIR/plan-review-feature-context.txt` by concatenating the resolved feature file with a `## Brainstorm synthesis (additive; optional)` section, then uses that merged path for `scout-plan-archetypes-wrapper.sh` (`--description-file`) and `dispatch-plan-review-panel.sh` (`--feature-file`). When `brainstorm.md` is absent or empty, `--feature-file` (or the default `feature-description.txt`) is used unchanged.

## Outline

Scout → panel dispatch → collect → dirty-tree checkpoint → TSV → findings → dedup → split in-scope/OOS → aggregate (`--input-mode plan`) → ballot → `dispatch-plan-voters.sh` → dirty-tree checkpoint → `tally-plan-review.sh` → final KVs.

The voter handoff binds `VOTER_N_PATH`, `VOTER_N_TOOL`, and `VOTER_N_STATUS`
from `dispatch-plan-voters.sh` stdout for N=1..3. The loop does not use the
legacy compacted `VOTER_PATHS_FILE` for the tally argv. For each non-failed
slot with a path, it emits `--voter <SLOT>:<PATH>` in slot order plus
`--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-$ROUND_NUM/findings-classification.tsv"`.
`tally-plan-review.sh` keys the forensic TSV columns from the declared
`--voter` slot labels, so misleading basenames cannot override the canonical
`Claude -> v1`, `Codex -> v2`, `Cursor -> v3` mapping. Waterfall fallback tool
identity remains visible via `vN_tool`.

If the 0-judge main-agent path reruns tally, it uses
`--voter MainAgent:$DESIGN_TMPDIR/voter-main-agent.txt`. Schema details and
`vN_tool` semantics are owned by `tally-plan-review.md`.

## Scope

Introduced for #2676; absorbs aggregator use in /design (`aggregate-findings.sh` with `--input-mode plan` per dialectic DECISION_1) and Voter 1 subprocess launch via `dispatch-plan-voters.sh`.

## Makefile

`make test-plan-review-loop`

## Harness

`skills/design/scripts/test-plan-review-loop.sh` exercises argv validation, a stubbed end-to-end path (optional `LARCH_PLAN_REVIEW_SCOUT_SH`, `LARCH_PLAN_REVIEW_DISPATCH_PANEL_SH`, `LARCH_PLAN_REVIEW_COLLECT_SH`, `LARCH_PLAN_REVIEW_DISPATCH_VOTERS_SH`, `LARCH_PLAN_REVIEW_TALLY_SH` pointing at test doubles), zero-finding vs single-finding ballots with real `tally-plan-review.sh`, panel-failed header-only artifact materialization, tally failure recovery KVs, and degraded `voting-tally.md` materialization when the tally stub exits non-zero. It is not a full production panel simulation.

## Edit-in-sync

Keep this file aligned with `plan-review-loop.sh` behavior and argv.
