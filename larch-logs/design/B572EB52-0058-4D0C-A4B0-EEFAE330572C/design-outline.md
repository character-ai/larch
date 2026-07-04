## Proposed Design Outline

### Goals
- Classify the 3 named neither-tier references (sentinel-host-table.md, step2b-drafter-failsafe.md, dialectic-clarifier.md) plus the additional confirmed gaps from the audit (final-summary-emit.md for design, checks-repair-loop.md, extracted-script-registry.md, phantom-probe.md, orchestrator-never.md for implement, run-id-flag.md for review).
- Generalize the classifier's existing "see X only for background" convention into a broader "load/see/read X only for/when/after/before Y" pattern so future similarly-phrased references stop falling through silently.
- Fix the `checks-repair-loop.md` gap at its root: the implement macro-section suppression drops matches entirely instead of marking them conditional (unlike design's equivalent mechanism), hiding a MANDATORY directive invoked from 3 call sites.
- Regenerate `python/skill-closure-baseline.json` so the dropped-file ratchet actually protects these files going forward.

### Non-goals
- No new watchlist/manifest file format (established in the prior PR's design; stays with the existing prose-classifier approach).
- No change to growth-ratchet thresholds/metrics for already-tracked files.
- No whole-file tracking for `SECURITY.md` or `skills/shared/oos-acceptance-rubric.md` — documented as deliberate exclusions (repo-root policy file with only one relevant section; rubric criteria already inlined at its call site), not silently dropped.

### Approach sketch
- `python/larch/lint/lint_skill_closure_growth.py`: widen the background-reference regex (trigger verbs `see`/`load`/`read`; connectors `for`/`when`/`after`/`before`) so it covers dialectic-clarifier.md and (after minor SKILL.md rephrasing) the other maintainer-only/conditional references.
- Same file: change `_update_implement_scan_state` to mark suppressed macro sections as *conditional* (mirroring `_update_design_scan_state`'s `conditional_section_depth` mechanism) instead of fully skipping their lines, fixing `checks-repair-loop.md` without duplicating prose.
- Same file: extend `_narrow_directive_matches` so `design` also recognizes the existing "follow ... final-summary-emit.md" pattern already used for `implement`.
- `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md`: minimal rephrasing so each flagged reference restates its filename directly inside a recognized qualifying clause (no behavior change, wording only).
- Regenerate `python/skill-closure-baseline.json` via `--write` once classifier + prose changes land.

### Surfaces in scope
- `python/larch/lint/lint_skill_closure_growth.py`
- `python/tests/lint/test_lint_skill_closure_growth.py`
- `python/skill-closure-baseline.json`
- `skills/design/SKILL.md`
- `skills/implement/SKILL.md`
- `skills/review/SKILL.md`

### Open questions
- None.
