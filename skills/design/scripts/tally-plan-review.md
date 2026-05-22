# tally-plan-review.sh

## Purpose

`tally-plan-review.sh` is the design-local plan-review vote tally. It parses `### FINDING_N:` and `### OOS_N:` blocks from a ballot file, reads explicit voter outputs, writes plan-review artifacts under `$DESIGN_TMPDIR`, and renders the reviewer competition scoreboard.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=TALLY`
- `/design` Step 3 after `dispatch-plan-voters.sh` returns Voter 2/3 output paths

## Invariants

- Required arguments are `--ballot-file FILE` and `--design-tmpdir DIR`; `--voter-files FILE...` may be empty.
- Optional `--session-env-path FILE` enables nested-run OOS handoff.
- The parser supports design-local `### FINDING_N:` and `### OOS_N:` blocks. Voter files use anchored `ID: VOTE` lines (e.g. `FINDING_1: YES`); substring matching is rejected to prevent `FINDING_10` matching inside `FINDING_100`.
- Acceptance threshold comes from `scripts/lib-vote-tally.sh::classify_result`: 3+ eligible voters require 2+ YES; 2 eligible voters require unanimous YES; 1 eligible voter is a binding single-judge decision; 0 eligible voters emit `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` for main-agent adjudication.
- The quorum basis is the panel-level available voter count, not the per-finding non-`JUDGE_ERROR` response count. Per-judge `JUDGE_ERROR` fallbacks do not reduce the tier.
- Accepted in-scope findings are written to `accepted-plan-findings.md`.
- Rejected or neutral in-scope findings are written to `rejected-findings.md`.
- OOS visibility output is written to `oos.md`.
- Accepted OOS output is also written to `oos-accepted-design.md` locally and, when `--session-env-path` is provided, to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` so `ship-pr.sh` and `/implement` Step 9a.1 find it.
- When `--session-env-path` is provided and its `PREV_IMPLEMENT_TMPDIR` plus `session-id` resolve, the script best-effort writes a parent `/implement` `plan-review-tally` larch-log batch through `scripts/write-tally.sh` in HARD mode. The body contains `voting-tally.md` plus rejected plan findings, and the accepted/rejected counters count in-scope findings only. Flush failures append a `Warnings` entry to the parent `execution-issues.md` without changing the tally result.
- Accepted OOS blocks with an unfenced `focus-area = security` token are excluded from all public OOS outputs. Fenced occurrences (inside backtick or triple-backtick regions) are not load-bearing (Match discrimination false-positive guard).
- Scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected` (+1 per accepted item, -1 per rejected item).
- The rendered scoreboard columns are `Reviewer`, `Proposed`, `Accepted`, `Neutral/Exon`, `Rejected`, `OOS-Proposed`, `OOS-Accepted`, `OOS-Neutral/Exon`, `OOS-Rejected`, and `Score`.

## Makefile Wiring

The regression harness is `make test-tally-plan-review`, wired into `test-harnesses-1`.

## Harness

`test-tally-plan-review.sh` covers all-yes, mixed votes, tie/neutral, single-judge YES/NO/EXONERATE, 0-judge main-agent-required, no quorum reduction for per-judge `JUDGE_ERROR` fallbacks, OOS accepted/rejected, security-tagged OOS exclusion, HARD-path plan-review-tally batch flushing, and scoreboard rendering.

## Edit In Sync

Update this contract, `test-tally-plan-review.sh`, `skills/design/SKILL.md`, and `skills/design/references/plan-review.md` together when ballot or artifact formats change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
