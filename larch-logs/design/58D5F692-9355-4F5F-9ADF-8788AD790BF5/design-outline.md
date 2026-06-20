## Proposed Design Outline

### Goals
- Replace the flat `+1` per accepted reviewer finding with two tiers: `+2` high-severity, `+1` ordinary.
- Tier on panel-assessed severity (`blocker`/`major` → `+2`; `minor`/`nit`/`uncertain` → `+1`), not the reviewer's self-declared `body_severity`.
- Update scoreboard rendering and the competition docs to match.

### Non-goals
- No penalty scaling: rejected stays flat `-1`.
- No change to conditional-spawning rounds-3-4 pruning (keeps unweighted accepted-minus-rejected counts).
- No OOS weighting: OOS rows carry no severity, so they stay flat `+1`/`-1`.
- No config table, no third tier.

### Approach sketch
- Add one small severity-to-weight helper in `python/voting.py` keyed on the panel-consensus severity already present per finding in `findings-classification.tsv` (`v1_severity`/`v2_severity`/`v3_severity`).
- Apply the weight where the accepted score is computed (the `scoreboard_main` count loop and the `progress_report.py` scoreboard/score path) instead of `score += 1`.
- Preserve dedup: each contributing reviewer of a merged finding receives the same weighted points.

### Surfaces in scope
- `python/voting.py` (weight helper + `scoreboard_main`)
- `python/progress_report.py` (scoreboard score rendering)
- `python/review_pipeline.py` (review-side scoreboard wiring)
- `skills/shared/voting-protocol.md`, `docs/point-competition.md` (doc updates)
- Tests: `python/test_voting.py`, `python/test_progress_report.py`

### Open questions
- None. Round 1 resolved tier source, penalty, pruning, and OOS.
