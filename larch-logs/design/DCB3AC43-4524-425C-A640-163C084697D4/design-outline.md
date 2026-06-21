## Proposed Design Outline

### Goals
- Reward the sole finder of an accepted in-scope finding with a small experimental uniqueness bonus, so reviewers are incentivized to surface non-obvious findings instead of converging on the obvious shared `+1`.
- Keep the bonus off by default and operator-tunable, so it ships as a monitorable experiment.
- Apply the rule once, shared across both `/design` plan review and `/review` code review scoring.

### Non-goals
- No change to OOS scoring (flat `+1`/`0`/`-1`); OOS fate is #4776's domain.
- No change to vote classification, thresholds, or `classify_result`.
- Not default-on; no change to any score when the env var is unset or `0`.
- No change to reviewer-pruning math (stays unweighted accepted-minus-rejected).

### Approach sketch
- Add one shared knob in `python/voting.py`: env var `LARCH_UNIQUE_FINDER_BONUS` (float, default `0` = off; positive value enables and sizes it; suggested experimental value `+0.25`), plus a small helper to parse it.
- "Sole finder" = an accepted in-scope finding whose restored proposer attribution names exactly one reviewer (not merged across reviewers during dedup).
- In both tally layers (`plan_review_tally.py`, `review_tally.py`), when the bonus is enabled, add it to the proposer's `Score` for each accepted in-scope sole-finder finding. Additive on top of base `+1`/`+2`.
- Monitoring without schema churn: keep the existing scoreboard table byte-stable; when the bonus is active, emit a one-line note under the scoreboard (knob value + count of sole-finder findings rewarded). No new TSV/table column.
- Update the in-scope shared-credit sections of `docs/point-competition.md` and `skills/shared/voting-protocol.md` only; leave the OOS sections for #4776.

### Surfaces in scope
- `python/voting.py` (knob + helper; possibly score-formatting reuse)
- `python/plan_review_tally.py` (sole-finder detection + bonus in `_scoreboard`)
- `python/review_tally.py` (same for code review)
- `docs/point-competition.md`, `skills/shared/voting-protocol.md` (in-scope sections)
- Tests: `python/test_voting.py`, plus the tally test harnesses

### Open questions
- Monitoring surface: the one-line scoreboard note (proposed above) vs a heavier per-reviewer breakdown. Leaning to the lighter note to keep the table schema and byte-compat tests stable. Will settle during drafting.
