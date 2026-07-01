## Proposed Design Outline

### Goals
- Reclassify the four mislabeled references (decompose-panel.md, validator-failure.md, settle-rc-dispatch.md, step2b5-rc-handling.md) from eager to conditional in the closure scanner.
- Split `skill-closure report` output into an eager section (ratcheted) and a conditional section (reported only).
- Regenerate `python/skill-closure-baseline.json` so eager metrics reflect only common-path references.

### Non-goals
- No edits to SKILL.md or any other skill markdown file (machine markers are out of scope; "Detector and baseline only").
- No changes to the JSON baseline schema (same keys, regenerated values for design skill only).
- No changes to `/implement` skill closure (unaffected).

### Approach sketch
- Extend `_line_is_conditional` with a suffix check for "(if not already loaded" patterns (fixes settle-rc-dispatch.md occurrences).
- Add section-scoped tracking to `ScanState` and `_update_scan_state`: when a heading matches CONDITIONAL_SECTION_HEADINGS ("Split-path (decomposition panel)", "Plan command validator failure (shared)"), mark entries as conditional until a heading of equal or lower depth ends the section.
- Add "retained" to `CONDITIONAL_TEXT_RE` (fixes step2b5-rc-handling.md line 349 where the prefix "Retained callers..." lacks conditional keywords).
- Change `parse_direct_markdown_references` to return `(eager_refs, conditional_refs)` as two tuples; propagate through `scan_skill` and `SkillClosureResult` (add `conditional_files`).
- Update `_print_report` to show two sections.
- Update `_growth_violations` to compare only eager metrics.
- Update tests and regenerate baseline.

### Surfaces in scope
- `python/larch/lint/lint_skill_closure_growth.py`
- `python/skill-closure-baseline.json`
- `python/tests/lint/test_lint_skill_closure_growth.py`

### Open questions
- None.
