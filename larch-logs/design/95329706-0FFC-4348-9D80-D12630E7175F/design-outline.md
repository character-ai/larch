## Proposed Design Outline

### Goals
- Reduce `skills/design/SKILL.md` line count by 10–15% (80–120 lines, ~790 → 670–710) via in-place prose compression.
- Add a CI closure-size ratchet in `scripts/test-design-structure.sh` to prevent regression.
- Preserve all contract tokens, KEY=value grammars, fence shapes, step numbers, Print: directives, and anti-halt/NEVER rule content.

### Non-goals
- Structural fold/relocate (out of scope per issue).
- Compressing `skills/implement/SKILL.md` or any `references/` files.
- Removing deliberately-duplicated compaction-resilience content (NEVER rules, anti-halt reminders).

### Approach sketch
- Add a `wc -l` ratchet check to `scripts/test-design-structure.sh` (same pattern as `test-review-structure.sh`); threshold set to post-compression count.
- Whole-file prose pass: compress anti-halt continuation paragraph, Step 0 prose, Step 3 routing prose, and hedging throughout.
- Apply Strunk & White: active voice, cut qualifiers, shorten run-on sentences, prefer bullets where prose currently accumulates multi-clause lists.
- Verify `make test-design-structure` passes at post-compression count.

### Surfaces in scope
- `skills/design/SKILL.md` (edits to prose only)
- `scripts/test-design-structure.sh` (add ratchet check)
- `scripts/test-design-structure.md` (update sibling doc to reflect new check)

### Open questions
- None.
