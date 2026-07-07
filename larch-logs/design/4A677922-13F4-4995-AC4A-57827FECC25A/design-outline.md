## Proposed Design Outline

### Goals
- Block `/implement` from merging onto red main; repair red main in-run on the current branch.
- Treat any test that fails then passes with no code change as a nondeterminism defect to root-cause before ship.
- Align scope doctrine (rubric, execution-issues, ship-ci-fix) so reviewers and the orchestrator classify broken/flapping main as in-scope work.

### Non-goals
- Post-merge push-run watch (deferred per operator decision).
- `/release` skill adoption (separate follow-up issue).
- Changes to `ARCHITECTURAL_INVARIANTS.md` (owned by #6476; note dependency if needed).

### Approach sketch
- Add `python3 python/cli.py ci main-health` verb: reads the latest completed push-run conclusion on the default branch; emits `MAIN_CI_STATUS=pass|fail|pending|error` and `MAIN_FAILED_RUN_ID=`.
- Call main-health at preflight (before the plan is accepted) and pre-merge (inside the ship loop before the merge action). On `fail`, pass the failed run ID to the existing CI-fix machinery; the repair merges with the feature PR. On infra failure (non-repo cause), bail to operator.
- Update `decide()` in `ci_monitor.py` to accept a `main_broken` flag; block merge when the flag is set.
- Update `evaluate_failure` / `ci_agentic_fix.py`: detect fail-then-pass-with-no-code-change (flaky pattern); root-cause from the failed run log instead of consuming a retry slot.
- Update prose: `ship-pr-ci-fix.md` (flaky-as-retry-budget → flaky-as-defect), `execution-issues-tracking.md` (log-only-transient scope narrowed to infra), `review-acceptance-rubric.md` gate-5 + regenerate all consumer files.

### Surfaces in scope
- `python/larch/implement/ci.py`
- `python/larch/implement/ci_monitor.py`
- `python/larch/implement/preflight.py`
- `python/larch/implement/ship_merge.py`
- `python/larch/implement/ci_agentic_fix.py`
- `skills/implement/SKILL.md`
- `skills/implement/references/ship-pr-ci-fix.md`
- `skills/implement/references/execution-issues-tracking.md`
- `skills/shared/review-acceptance-rubric.md` + generated consumer files
- Possibly `python/larch/implement/ship_pr.py` (pre-merge call site)

### Open questions
- None.
