## Proposed Design Outline

### Goals
- Measure the voting panel: give each voter a per-run agreement metric (its votes vs the panel verdict) and flag chronic outliers.
- Emit a live per-run voter scoreboard during the tally, beside the existing reviewer scoreboard.
- Add a post-hoc analyzer that aggregates voter agreement across committed run-logs and flags chronic outlier voters.

### Non-goals
- No realized-outcome / issue-fate / revert calibration (the richer version; deferred).
- No change to vote thresholds, acceptance rules, dedup, or reviewer scoring.
- No token-allocation or spawning changes; this measures and reports only.
- No change to `/fluff-analysis`.

### Approach sketch
- Put the agreement math once in `python/voting.py`: per voter, agree/disagree vs the panel verdict, with neutral verdicts and single/zero-voter panels handled (excluded from the denominator).
- Call it from both tally drivers to write a live voter-scoreboard artifact per run; additive only, no change to the `findings-classification.tsv` schema.
- New sibling skill `voter-calibration` (script modeled on `fluff-analysis`) scans `larch-logs/{design,implement}` classification TSVs, aggregates per-voter agreement, flags chronic outliers, prints a markdown report.

### Surfaces in scope
- `python/voting.py` (shared agreement helper + voter-scoreboard renderer)
- `python/plan_review_tally.py`, `python/review_tally.py` (live per-run scoreboard wiring)
- `skills/voter-calibration/` (new skill: SKILL.md + script + offline test)
- `docs/voting-process.md`, `docs/point-competition.md` (prose: panel is now measured)

### Open questions
- None.
