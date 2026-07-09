## Proposed Design Outline

### Goals
- Add `I-Stale-1` to `ARCHITECTURAL_INVARIANTS.md` under `## Workflow integrity`.
- Cite only verified evidence issues and the existing `note_consumable`/`_staged_fingerprint_valid` pattern in `architectural_guidelines.py`.

### Non-goals
- No mechanical enforcement changes in this PR; consumer gaps are noted in the PR body and followed up separately.
- No changes to `ARCHITECTURAL_GUIDELINES.md` or any Python source.
- No new tests for the invariant text itself.

### Approach sketch
- Append `### I-Stale-1: ...` heading and body after `I-Pause-1` in `## Workflow integrity`.
- Adapt the issue-proposed wording per readability-style.md (shorter sentences, no em dashes).
- Verify `I-Stale-1` matches `INVARIANT_HEADING_RE` before writing.

### Surfaces in scope
- `ARCHITECTURAL_INVARIANTS.md`

### Open questions
- None.
