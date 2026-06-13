## Proposed Design Outline

### Goals
- Port 10 bash scripts (~5.5k LOC) to importable Python modules with `cli.py` verbs.
- Cut over `/review` SKILL.md Steps 1-3 to direct `python3 cli.py review ...` calls.
- Replace 6 bash test harnesses with pytest; delete absorbed bash scripts and harnesses.

### Non-goals
- Porting `prune-nit-findings.sh` or `reviewer-prune.sh` (separate later issue).
- Porting C1a dispatch-engine scripts (`dispatch-with-waterfall.sh`, `collect-agent-results.sh`, `launch-review.sh`); those are C1a sub-issues #4165-4170.
- Changing the `--subagent` / SendMessage contract in the `/review` SKILL.

### Approach sketch
- Create `python/review_pipeline.py`: gather_context, dispatch_panel, collect_findings, check_reviewer_failure_threshold, review_core; dispatch_panel calls `run_waterfall()` from `agents.py`.
- Create `python/review_aggregate.py`: aggregate_findings (includes phrase-list constant ported from `aggregate-findings-phrases.inc.bash`).
- Port tally-code-votes, emit-tally, log-phase into `python/review_tally.py`.
- Port `scripts/compose-review-findings.sh` into `python/compose_review.py`.
- Add `("review", "...")` verbs in `cli.py`; cut over SKILL.md Steps 1-3 call sites.

### Surfaces in scope
- `python/review_pipeline.py` (new)
- `python/review_aggregate.py` (new)
- `python/review_tally.py` (new)
- `python/compose_review.py` (new)
- `python/cli.py` (new verbs)
- `skills/review/SKILL.md` (cutover Steps 1-3)
- `python/migrated-scripts.tsv` (stale-ref entries)
- All 10 absorbed `.sh`/`.md` files deleted; 6 test harness `.sh`/`.md` deleted

### Open questions
- None.
