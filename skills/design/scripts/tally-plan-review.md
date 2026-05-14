# tally-plan-review.sh

## Purpose

`tally-plan-review.sh` is the design-local plan-review vote tally. It parses `### FINDING_N:` and `### OOS_N:` blocks from a ballot file, reads explicit voter outputs, writes plan-review artifacts under `$DESIGN_TMPDIR`, and renders the reviewer competition scoreboard.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=TALLY`
- `/design` Step 3 after `dispatch-plan-voters.sh` returns Voter 2/3 output paths
- `skills/design/references/heavy-worker.md` during subagent plan review

## Invariants

- Required arguments are `--ballot-file FILE`, `--voter-files FILE...`, and `--design-tmpdir DIR`.
- Optional `--session-env-path FILE` enables nested-run OOS handoff.
- The parser supports design-local `### FINDING_N:` and `### OOS_N:` blocks. Voter files use anchored `ID: VOTE` lines (e.g. `FINDING_1: YES`); substring matching is rejected to prevent `FINDING_10` matching inside `FINDING_100`.
- Acceptance threshold: 2+ YES for 3+ eligible voters; unanimous YES (2/2) for exactly 2 eligible voters; all findings rejected when fewer than 2 eligible voters.
- Accepted in-scope findings are written to `accepted-plan-findings.md`.
- Rejected or neutral in-scope findings are written to `rejected-findings.md`.
- OOS visibility output is written to `oos.md`.
- Accepted OOS output is also written to `oos-accepted-design.md` locally and, when `--session-env-path` is provided, to `$(dirname "$SESSION_ENV_PATH")/oos-accepted-design.md` so `ship-pr.sh` and `/implement` Step 9a.1 find it.
- Accepted OOS blocks with an unfenced `focus-area = security` token are excluded from all public OOS outputs. Fenced occurrences (inside backtick or triple-backtick regions) are not load-bearing (Match discrimination false-positive guard).
- Scoreboard score formula: `accepted + oos_accepted - rejected` (+1 per accepted in-scope, +1 per accepted OOS, -1 per rejected).
- The rendered scoreboard columns are `Reviewer`, `Proposed`, `Accepted`, `Neutral/Exon`, `Rejected`, `OOS-Proposed`, `OOS-Accepted`, and `Score`.

## Makefile Wiring

The regression harness is `make test-tally-plan-review`, wired into `test-harnesses-1`.

## Harness

`test-tally-plan-review.sh` covers all-yes, mixed votes, tie/neutral, voter failure, OOS accepted/rejected, security-tagged OOS exclusion, and scoreboard rendering.

## Edit In Sync

Update this contract, `test-tally-plan-review.sh`, `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, and `skills/design/references/heavy-worker.md` together when ballot or artifact formats change.
