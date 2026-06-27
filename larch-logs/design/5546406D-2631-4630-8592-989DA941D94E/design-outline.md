## Proposed Design Outline

### Goals
- Add regression tests for 4 chronic bug families (notification/sentinel, Gantt/report render, aggregator, lint-fix) that encode class invariants, not just fix-specific assertions.
- Each test must fail when the defect pattern is reintroduced and pass on clean code.
- All new tests run in CI under existing `make` targets.

### Non-goals
- Fixing the underlying bugs (tests only).
- Covering the other 8 bug families in the 12-family table.
- Replacing or rewriting existing test infrastructure.

### Approach sketch
- **Notification/sentinel**: Add literal-pin clauses in `test-implement-anti-polling-rule.sh` (and/or a new sibling script) that assert the empty-output guard clause is present in `skills/design/SKILL.md` and `skills/shared/design-background-wait.md`. Target the specific tokens that keep getting dropped: `task output is empty`, `end the turn without probing`, and the `#5240` reference.
- **Gantt/report render**: Extend `python/test_gantt.py` and `python/test_final_report.py` with golden-output tests: verify that each rendered phase block contains non-empty label, start, and duration fields, and that the Gantt chart block is non-empty even for minimal input.
- **Findings-aggregator**: Extend `python/test_review_aggregate.py` with contract tests for the three named invariants: missing-reviewer-attribution (partial input still emits attribution), dedup-fallback (semantic duplicates merged, not duplicated), and semantic-validation rejection (invalid findings are rejected, not silently passed).
- **Lint-fix/checks loop**: Extend `python/test_checks.py` with assertions that fast-fail exits before running all checks on the first failure, and that the `RELEVANT_CHECKS` table includes every required check key.

### Surfaces in scope
- `scripts/test-implement-anti-polling-rule.sh` (or a new `scripts/test-notification-sentinel-invariant.sh`)
- `python/test_gantt.py`
- `python/test_final_report.py`
- `python/test_review_aggregate.py`
- `python/test_checks.py`
- Possibly `scripts/test-implement-anti-polling-rule.md` (sibling doc update)
- `Makefile` (if a new script target is added)

### Open questions
- None.
