## Proposed Design Outline

### Goals
- Stop the silent drop of the architectural-guideline note when HEAD drifts after Step 7a staging.
- When the durable note cannot be delivered for the shipped HEAD, surface a clear "note dropped: HEAD drifted after staging" notice in both the PR body and the final report.

### Non-goals
- Re-authoring the assessment against current HEAD (LLM/prompt-side; out of scope).
- Mechanically re-pinning the stale staged assessment to the new HEAD.
- Changing Phase A staging or the prompt-side reassessment-on-drift contract in implement SKILL.md.

### Approach sketch
- Add a mechanical drift-detection helper in architectural_guidelines.py that reports "staged assessment present but durable note not deliverable for shipped HEAD (drift)".
- In ship.py _pin_and_load_guidelines_note, on a drop with a staged assessment present, return a dropped-notice string instead of "".
- Render the notice under the existing "## Architectural guidelines" heading in both pr_body.py (compose_pr_body) and final_report.py (_architectural_guidelines_section).
- Keep the existing Warnings line; the notice is additive.

### Surfaces in scope
- python/architectural_guidelines.py, python/ship.py, python/pr_body.py, python/final_report.py
- Tests: test_architectural_guidelines.py, test_ship.py, test_pr_body.py, test_final_report.py

### Open questions
- None.
