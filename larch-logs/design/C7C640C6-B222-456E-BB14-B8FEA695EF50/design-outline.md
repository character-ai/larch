## Proposed Design Outline

### Goals
- Remove vendor/model attribution from voter-facing ballots across `/design` plan review, `/review`, and `/implement` Step 5 code review, so judges cannot favor same-vendor proposals.
- Preserve proposer attribution out of band for scoring, the competition scoreboard, and accepted/rejected/OOS audit and issue-filing artifacts.
- Stay backward-compatible: legacy ballots with no sidecar still tally via the existing reviewer parser.

### Non-goals
- No body-text scrubbing. Legitimate `Codex`/`Cursor`/`Claude` references in finding bodies survive unchanged.
- No change to vote thresholds, scoring math, or the "no self-voting exclusion" rule.
- No empirical self-vs-other measurement pass (deferred to a follow-up comment per the issue).

### Approach sketch
- Add shared helpers to `python/voting.py`: neutralize the `- **Reviewer**:` line to a fixed neutral token (keep the line, drop the vendor value), build/read a proposer-map sidecar keyed by `FINDING_N`/`OOS_N`, and resolve proposer (sidecar first, `reviewer_for_block` fallback).
- `/design`: write `proposer-map.tsv` from the unstripped ballot, then neutralize `$DESIGN_TMPDIR/ballot.txt` before voter dispatch; pass the sidecar to tally. MAV reads the same neutralized ballot.
- `/review` + `/implement` Step 5: after collect/aggregate/prune and before voter dispatch, write the sidecar and neutralize `findings.md`; pass the sidecar to every tally call.
- Tallies read proposer from the sidecar for classification + scoreboard and restore the original reviewer line for accepted/rejected/OOS artifacts.

### Surfaces in scope
- `python/voting.py` (shared helpers).
- `/design`: `python/plan_review_round.py`, `python/plan_review_tally.py`.
- `/review` + Step 5: `python/review_pipeline.py`, `python/review_tally.py`.
- Docs/refs: `skills/shared/voting-protocol.md`, `docs/voting-process.md`, `docs/point-competition.md`, `skills/design/references/plan-review.md`, `skills/review/SKILL.md`, `skills/implement/references/step5-review-branches.md`.
- Tests: `python/test_voting.py`, `python/test_plan_review.py`, `python/test_review_tally.py`, `python/test_review_pipeline.py`, `python/test_agent_voters.py`.

### Open questions
- Exact neutral token value (e.g. `Reviewer` vs `anonymous`). Plan drafting will pick one fixed token.
