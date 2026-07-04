## Proposed Design Outline

### Goals
- Correct the version floor in #6261 Preconditions from `>= v52.4.6` to `>= v52.4.7`.
- Reword criterion C in #6261 to name `final-summary.md` and the issue run-summary metadata comment as verification surfaces.
- Correct the baseline field list in #6261 (drop `rater: "fallback"` / `rater_tool: "bootstrap"`; keep `audit_evaluated: null` and `rater_model: "unknown"`).
- Mirror the version floor fix in #5993 wherever it echoes #6261 Preconditions.

### Non-goals
- No changes to larch runtime code (`ship.py`, `pr_body.py`, or any Python module).
- No changes to `docs/`, `README.md`, or other markdown files in the repo.
- No automated test additions.

### Approach sketch
- Read the current body of #6261 via `gh issue view`.
- Apply all three text corrections via `gh issue edit --body`.
- Read #5993 body; locate the mirrored version-floor text and apply the floor fix.
- Verify each edit with `gh issue view`.

### Surfaces in scope
- GitHub issue #6261 (Preconditions section, criteria A and C, baseline contrast note)
- GitHub issue #5993 (mirrored close condition referencing the version floor)

### Open questions
- None.
