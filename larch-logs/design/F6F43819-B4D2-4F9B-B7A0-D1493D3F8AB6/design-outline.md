## Proposed Design Outline

### Goals
- Extend `skill-closure report` / `lint skill-closure-growth` to cover `/review` as a third gated skill (eager plus conditional rows), reusing the existing per-skill scan/baseline machinery.
- Add one panel-tier row (`agents/*.md`, `reviewer-templates*.md`, `voting-protocol.md`) to the same baseline and growth lint.
- Fix the four named eager-classifier gaps (missed hot-path shared reads) and the one default-path misclassification (`preflight-plan-audit.md`).

### Non-goals
- No prose compression of any panel-tier or SKILL.md file. That is the B-group children (#5978-#5981).
- No new CLI verb. Reuse `skill-closure report` and `lint skill-closure-growth`.
- No rewrite of the directive-matching engine. Targeted regex/pattern additions only for the named gaps.

### Approach sketch
- Add `"review"` to `GATED_SKILLS` in `python/larch/lint/lint_skill_closure_growth.py`. `scan_skill()` already walks any skill's `SKILL.md` directives, so review's row falls out of the existing machinery.
- Add a panel-tier scan path that sums a fixed file set (agents glob plus the three named shared files) into a baseline row, reusing the metric, report, and growth-check code paths.
- Extend directive-matching to catch "follow `X`" and "use `X` for Y" phrasing, and correct the `force_requested=false`-is-default misclassification. Regenerate `python/skill-closure-baseline.json` for every row.

### Surfaces in scope
- `python/larch/lint/lint_skill_closure_growth.py`
- `python/skill-closure-baseline.json`
- `python/tests/lint/test_lint_skill_closure_growth.py`
- `docs/linting.md`

### Open questions
- None.
