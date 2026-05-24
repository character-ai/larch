# plan-review-loop.sh

**Consumer**: `/design` Step 3 (`review_budget=full`) — single-pass plan-review driver.

**Primary callers**: `skills/design/SKILL.md` Step 3 (foreground Bash block).

## Invariants

- Writes session-root artifacts under `$DESIGN_TMPDIR/`: `ballot.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md` (same names and parse contracts as the pre-refactor inline flow).
- Never revises `plan.txt` (Gate B owns plan revision).
- Honors `LARCH_AGGREGATOR_DISABLED=1` by skipping `aggregate-findings.sh` and setting `AGGREGATOR_STATUS=disabled`.
- Emits stdout key/value lines: `LOOP_STATUS`, `ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `TALLY_PLAN_REVIEW_STATUS`, `VOTING_TALLY_FILE`, `VOTER_1_PARSE_RATE_STATUS`, plus optional `WARN=` lines.

## Argv

`--design-tmpdir`, `--plan-file`, optional `--feature-file`, `--round-num` (default 1), `--codex-present`, `--cursor-present`, optional `--timeout` (panel + collect; default 1860), `--help`.

## Outline

Scout → panel dispatch → collect → dirty-tree checkpoint → TSV → findings → dedup → split in-scope/OOS → aggregate (`--input-mode plan`) → ballot → `dispatch-plan-voters.sh` → dirty-tree checkpoint → `tally-plan-review.sh` → final KVs.

## Scope

Introduced for #2676; absorbs aggregator use in /design (`aggregate-findings.sh` with `--input-mode plan` per dialectic DECISION_1) and Voter 1 subprocess launch via `dispatch-plan-voters.sh`.

## Makefile

`make test-plan-review-loop`

## Harness

`skills/design/scripts/test-plan-review-loop.sh` (offline stubs).

## Edit-in-sync

Keep this file aligned with `plan-review-loop.sh` behavior and argv.
