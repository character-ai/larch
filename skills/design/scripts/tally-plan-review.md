# tally-plan-review.sh

## Purpose

`tally-plan-review.sh` is the design-local plan-review vote tally. It parses `### FINDING_N:` and `### OOS_N:` blocks from a ballot file, reads explicit voter outputs, writes plan-review artifacts under `$DESIGN_TMPDIR`, and renders the reviewer competition scoreboard.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=TALLY`
- `/design` Step 3 after `dispatch-plan-voters.sh` returns Voter 2/3 output paths

## Invariants

- Required arguments are `--ballot-file FILE` and `--design-tmpdir DIR`; `--voter SLOT:FILE` may repeat with `SLOT` in `Claude`, `Codex`, `Cursor`, or `MainAgent`. `--voter-files FILE...` remains as a deprecated compatibility fallback and emits a stderr warning.
- Repeating the same `--voter SLOT:FILE` slot is invalid and exits 2 before tallying; otherwise panel outcomes can diverge from the fixed `vN_*` forensic columns.
- `--findings-classification-out FILE` optionally selects the forensic TSV path. Without it, the script writes `$DESIGN_TMPDIR/plan-review/round-1/findings-classification.tsv` and creates the parent directory internally.
- The parser supports design-local `### FINDING_N:` and `### OOS_N:` blocks. Voter files use anchored `ID: VOTE` lines (e.g. `FINDING_1: YES`); substring matching is rejected to prevent `FINDING_10` matching inside `FINDING_100`.
- Acceptance threshold comes from `scripts/lib-vote-tally.sh::classify_result`: 3+ eligible voters require 2+ YES; 2 eligible voters require unanimous YES; 1 eligible voter is a binding single-judge decision; 0 eligible voters emit `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` for main-agent adjudication.
- The quorum basis is the panel-level available voter count, not the per-finding non-`JUDGE_ERROR` response count. Per-judge `JUDGE_ERROR` fallbacks do not reduce the tier.
- Accepted in-scope findings are written to `accepted-plan-findings.md`.
- Non-accepted in-scope findings are written to `rejected-findings.md`.
- OOS visibility output is written to `oos.md`.
- Accepted OOS output is written to `oos-accepted-design.md` under `$DESIGN_TMPDIR`.
- Accepted OOS blocks with an unfenced `focus-area = security` token are excluded from all public OOS outputs. Fenced occurrences (inside backtick or triple-backtick regions) are not load-bearing (Match discrimination false-positive guard).
- Scoreboard score formula: `accepted + oos_accepted - rejected - oos_rejected` (+1 per accepted item, -1 per rejected item).
- The rendered scoreboard columns are `Reviewer`, `Proposed`, `Accepted`, `Exonerated`, `Rejected`, `OOS-Proposed`, `OOS-Accepted`, `OOS-Exonerated`, `OOS-Rejected`, and `Score`.
- `findings-classification.tsv` schema is `finding_id`, `finding_reviewers`, `voting_result`, then five columns for each fixed voter slot: `v1_*` = Claude, `v2_*` = Codex, `v3_*` = Cursor. `MainAgent` votes contribute to tally outcomes but do not populate vN forensic columns. The `vN_vote` cells reuse the same anchored vote parser as panel tallies; the rating-axis cells come from `parse-judge-vote-and-rating.sh`.
- `finding_reviewers` is reviewer attribution from the ballot block; vN columns are voter/judge identity. Missing slots leave empty vN cells; slots are never compacted.
- Zero-judge fallback writes one TSV row per ballot entry with `voting_result=classify_result(0,0,0,0)` (`rejected`) and all vN cells empty. Empty ballots write the header only.
- TSV rows are sorted numerically by `FINDING_*` first, then `OOS_*`. Voter-sourced cells and `finding_reviewers` are normalized for TSV by replacing tabs with spaces and stripping newlines.
- Whenever `--design-tmpdir` has been validated, `voting-tally.md` is materialized with at least the degraded header (`# Plan Review Voting Tally` plus a one-line abort note) before any non-zero exit. The missing-required-args and unknown-argument branches are exempt because `$DESIGN_TMPDIR` may be empty.
- Once `--design-tmpdir` and the classification output path are known, abort paths rewrite `findings-classification.tsv` to the canonical header-only form so stale forensic rows from a prior successful tally cannot survive a later failure.
- `mkdir -p "$DESIGN_TMPDIR"` runs as the first action after argv validation so all subsequent exit paths (including the ballot/voter-unreadable and split-failure branches) can safely write to it.

## Makefile Wiring

The regression harness is `make test-tally-plan-review`, wired into `test-harnesses-9`.

## Harness

`test-tally-plan-review.sh` covers all-yes, mixed votes, split-panel ties, single-judge YES/NO/EXONERATE, 0-judge main-agent-required, no quorum reduction for per-judge `JUDGE_ERROR` fallbacks, OOS accepted/rejected, security-tagged OOS exclusion, scoreboard rendering, malformed-ballot abort tally stub, missing-ballot abort tally stub, duplicate-slot rejection, `--voter SLOT:PATH`, deprecated `--voter-files`, custom/default classification output paths, and the `finding_reviewers` TSV schema.

`test-findings-classification.sh` covers the parser contract, fixed vN mapping, `vN_vote` parity with tally semantics on partial rows, partial-axis uncertainty, 0-judge and 0-finding TSV behavior, OOS rows, deterministic row order, and sanitization.

## Edit In Sync

Update this contract, `test-tally-plan-review.sh`, `skills/design/SKILL.md`, and `skills/design/references/plan-review.md` together when ballot or artifact formats change.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
