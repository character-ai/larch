## Proposed Design Outline

### Goals
- Cap all difficulty tiers (TRIVIAL, MODERATE, HARD) at exactly 2 review rounds
- Remove difficulty as a factor in review round count across /design, /implement, and /review

### Non-goals
- Changing escalation trigger logic (escalation still promotes panel quality for the available rounds)
- Changing any other tier-differentiated behavior (Codex model role, panel shape, threshold panel)
- Removing or restructuring the difficulty system

### Approach sketch
- Change `DIFFICULTY_TIER_CEILINGS[HARD]` from `3` to `2` in `python/larch/core/config.py`
- Update tests asserting `tier_ceiling(HARD) == 3` and `round_cap: 3`
- Update skill doc prose ("cap 2/2/3", "HARD caps at 3", "3-round cap") to "2/2/2" / "cap 2"

### Surfaces in scope
- `python/larch/core/config.py` — one-line constant change
- `python/tests/calibration/test_difficulty.py` — test assertions
- `python/tests/calibration/test_difficulty_calibration.py` — report output assertions
- `python/tests/review/test_plan_review.py` — comment referencing "HARD's 3 rounds"
- `skills/design/references/plan-review.md` — prose "2/2/3" and "cap 3"
- `skills/design/SKILL.md` — prose "HARD caps at 3"
- `skills/review/SKILL.md` — prose "2/2/3" and "HARD's 3-round cap"
- `skills/implement/SKILL.md` — prose "2/2/3" and "HARD's 3-round cap"

### Open questions
- None.
