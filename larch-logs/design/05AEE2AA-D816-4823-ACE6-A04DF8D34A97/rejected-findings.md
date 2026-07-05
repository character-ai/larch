### [Plan Review] FINDING_7

### FINDING_7: Canonical voting and scoring docs still describe the old severity and OOS rules
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The public voting and point-competition docs still describe the retired severity scale and the broader accepted-OOS filing/scoring behavior, so readers get instructions that conflict with the new live gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add docs/voting-process.md and docs/point-competition.md to firm updates; align severity, high-rate, OOS filing, and OOS scoring prose with major-only high and accepted-plus-major-fileable OOS.
  - From Codex-Pragmatic: Add `docs/point-competition.md` and `docs/voting-process.md` to UPDATED and revise their severity, OOS filing, final-summary audit, and scoring prose to match `major|minor|nit` and fileable-only OOS acceptance.


### [Plan Review] FINDING_9

### FINDING_9: Competition scoring still needs the provisional accepted-minor +1
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan’s file gate must not be copied into the scoreboard counter, or accepted-but-minor OOS would stop earning the provisional point that the competition docs still expect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: State explicitly in `review_tally.py` / `plan_review_tally.py` and `skills/shared/voting-protocol.md` that scoreboard +1 uses vote-accepted OOS while `OOS_ACCEPTED_COUNT`, accepted sinks, aggregate pool, and filing use the shared fileable predicate only; add a tally test with accepted-`minor` OOS scoring +1 but `OOS_ACCEPTED_COUNT=0`


