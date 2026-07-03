## Proposed Design Outline

### Goals
- Make `flags.md`-style demoted-but-extant references visible to the skill-closure classifier by classifying the existing "see `X.md` ... only for background" convention as a conditional reference.
- Add a mechanical lint check: fail when a file tracked in the last committed baseline (`files` or `conditional_files`) for a skill is absent from both lists in a fresh scan.
- Audit `design`/`implement`/`review` (the only skills the classifier scans) for other neither-tier reference files and fix them in this same change.
- Regenerate `python/skill-closure-baseline.json` to reflect the newly classified files.

### Non-goals
- No new watchlist/manifest file format — Step 1c resolved this in favor of extending the existing prose classifier (mechanical, self-documenting, no second source of truth to forget).
- No closure-tracking support for skills outside `RATCHETED_TARGETS` (design, implement, review, panel-tier) — structurally out of the classifier's scope.
- No change to existing growth-ratchet thresholds or metrics for already-tracked files.

### Approach sketch
- Extend `python/larch/lint/lint_skill_closure_growth.py`'s directive matcher with a new regex recognizing the "see `X.md` ... only for background" convention, classifying matches as conditional (not eager) references.
- Add a new violation check comparing baseline `files ∪ conditional_files` against live `files ∪ conditional_files` per skill; flag any baseline-tracked file missing from both live sets as a lint failure, alongside existing growth violations.
- Audit the three gated skills for other files referenced by relative path but absent from both tiers; classify each the same way (or note why not).
- Regenerate `python/skill-closure-baseline.json` via the existing `--write` flag once classification changes land.

### Surfaces in scope
- `python/larch/lint/lint_skill_closure_growth.py`
- `python/skill-closure-baseline.json`
- `python/tests/lint/test_lint_skill_closure_growth.py`
- `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md` (only if the audit finds other neither-tier files needing a phrasing or reference fix)

### Open questions
- None.
