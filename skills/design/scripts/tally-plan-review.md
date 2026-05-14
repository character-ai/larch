# tally-plan-review.sh

## Purpose

`tally-plan-review.sh` is the design-local plan-review vote tally. It parses `### FINDING_N:` and `### OOS_N:` blocks from a ballot file, reads explicit voter outputs, writes plan-review artifacts under `$DESIGN_TMPDIR`, and renders the reviewer competition scoreboard.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=TALLY`
- `/design` Step 3 after `dispatch-plan-voters.sh` returns Voter 2/3 output paths
- `skills/design/references/heavy-worker.md` during subagent plan review

## Invariants

- Required arguments are `--ballot-file FILE`, `--voter-files FILE...`, and `--design-tmpdir DIR`.
- The parser supports design-local `### FINDING_N:` and `### OOS_N:` blocks.
- Accepted in-scope findings are written to `accepted-plan-findings.md`.
- Rejected or neutral in-scope findings are written to `rejected-findings.md`.
- OOS visibility output is written to `oos.md`.
- Accepted OOS output is also written to `oos-accepted-design.md` for callers that need the accepted-only handoff.
- Accepted OOS blocks tagged with `focus-area = security` are excluded from both public OOS outputs.
- The rendered scoreboard columns are `Reviewer`, `Proposed`, `Accepted`, `Neutral/Exon`, `Rejected`, `OOS-Proposed`, `OOS-Accepted`, and `Score`.

## Makefile Wiring

The regression harness is `make test-tally-plan-review`, wired into `test-harnesses-1`.

## Harness

`test-tally-plan-review.sh` covers all-yes, mixed votes, tie/neutral, voter failure, OOS accepted/rejected, security-tagged OOS exclusion, and scoreboard rendering.

## Edit In Sync

Update this contract, `test-tally-plan-review.sh`, `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, and `skills/design/references/heavy-worker.md` together when ballot or artifact formats change.
