## Proposed Design Outline

### Goals
- Revise the token-allocation policy so future reviewer budget is allocated by precision-value (net-score-per-finding), not raw cumulative score.
- Add a short rationale to `docs/point-competition.md`: precision over volume, with the issue's worked example.
- State the two preconditions before allocation ships: value-weighted points (defines "value") and voter calibration (validates the signal).

### Non-goals
- No token-allocation code. None exists; allocation stays a "Future Plans" item.
- No change to the scoring tables, scoreboard schema, or the +2/+1/−1 point rules.
- No edits to the diagnostic "unchanged" mentions in `docs/voting-process.md` or `skills/voter-calibration/SKILL.md`.

### Approach sketch
- In `docs/point-competition.md` "Future Plans", replace the score-weighted sentence with a precision-value statement, then add a short rationale subsection (precision-vs-volume, worked example, dependency note).
- In `skills/shared/voting-protocol.md` Scoreboard, reword the one-line "weighted proportionally to reviewer scores" sentence to name precision-value (net-score-per-finding).
- Define net-score-per-finding inline: net competition score (Σ accepted − rejected, with the +2 major/blocker weight) divided by the reviewer's finding count.

### Surfaces in scope
- `docs/point-competition.md` (Future Plans section)
- `skills/shared/voting-protocol.md` (Scoreboard section)

### Open questions
- None.
