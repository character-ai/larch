## Proposed Design Outline

### Goals
- Port the /design plan-review loop core (~4.1k bash LOC, 15+ scripts) to stdlib-only Python modules with importable functions and `python3 cli.py` CLI verbs.
- Retire all absorbed bash scripts and sibling `.md` files; replace harnesses with pytest.
- Cut all call sites to direct `python3 cli.py plan-review ...` calls in the same commit.

### Non-goals
- Changing any existing KV enum value, `.step3-review-result.env` key, or per-round artifact structure.
- Migrating `design-step3-review.sh` beyond updating the `run-step3-review.sh` call site.
- Migrating assessor scripts (Step 3.6: `assess-plan-round.sh` etc.) or design lifecycle scripts (C3b scope).
- Moving `dedup-plan-lines.py` from `skills/design/scripts/` (deferred cleanup).

### Approach sketch
- Create `python/plan_review_panel.py`: panel dispatch, voter dispatch (absorbs `dispatch-plan-review-panel.sh`, `dispatch-plan-voters.sh`).
- Create `python/plan_review.py`: loop core + state + tally wrapper + round artifacts/timing + emit/finalize/preview + drift baseline + gate-B dedup + retally env (absorbs remaining 13 scripts).
- Register a `plan-review` domain in `python/cli.py` with per-verb entries for each absorbed operation.
- Update `design-step3-review.sh` to call `python3 cli.py plan-review run` instead of `run-step3-review.sh`.
- Stale-reference sweep: update all `.md` refs, Makefile targets, and bash wrappers; append to `migrated-scripts.tsv`.

### Surfaces in scope
- `python/plan_review.py` (new)
- `python/plan_review_panel.py` (new)
- `python/test_plan_review.py`, `python/test_plan_review_panel.py` (new)
- `python/cli.py` (new `plan-review` domain entries)
- `skills/design/scripts/design-step3-review.sh` (call site update only)
- All `.md` sibling files for absorbed scripts (deletion + stale-ref sweep)
- `python/migrated-scripts.tsv`, `Makefile`, `.github/workflows/ci.yaml`

### Open questions
- None.
