## Proposed Design Outline

### Goals
- Replace the gameable `wc -l` line-count assertion in `scripts/test-design-structure.sh` with an estimated-token check using the same `(len(text) + 3) // 4` formula as `lint_skill_closure_growth.py`.
- Ensure blank-line-only diffs produce no meaningful ratchet headroom.
- Update the sibling `test-design-structure.md` to document the new check.

### Non-goals
- No prose edits to `skills/design/SKILL.md`.
- No changes to `lint_skill_closure_growth.py` or `skill-closure-baseline.json`.
- No new CLI verbs or Python modules.

### Approach sketch
- In `scripts/test-design-structure.sh`, replace the `skill_lines=$(wc -l ...) ≤ 705` block with a Python one-liner that reads `SKILL_MD`, computes `(len(text) + 3) // 4`, and compares against `30131`.
- Keep the Python call as an inline `python3 -c` expression.
- Update the error message to name the token metric and threshold.
- Update `scripts/test-design-structure.md` to say "token count" instead of "line count".

### Surfaces in scope
- `scripts/test-design-structure.sh`
- `scripts/test-design-structure.md`

### Open questions
- None.
