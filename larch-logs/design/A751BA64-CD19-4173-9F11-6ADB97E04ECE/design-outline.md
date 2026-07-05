## Proposed Design Outline

### Goals
- Shipped `/implement --merge` PR body always carries a real architectural-guideline assessment (clean note or deviation list), never the "HEAD drifted" drop notice.
- A genuine deviation authored during the run reaches the PR body.
- Author the assessment once, against the final diff at stable HEAD, after the last Step 8b rebase.

### Non-goals
- No change to how `/design` reads, presents, or persists guideline assessments.
- No new drop-rate measurement tooling (re-measurement is post-merge operator validation).
- No ship-flow refactor beyond the architectural-guideline seam.

### Approach sketch
- Move assessment authoring from Step 7a Phase A staging to Step 8 compose time, after the final rebase, when HEAD and the shipped diff are stable.
- Retire the staged-assessment write, the diff-fingerprint pin, and the "HEAD drifted" drop notice in `architectural_guidelines.py` / `ship_guidelines.py`.
- Split the compose seam: `ship.py` materializes the final diff at stable HEAD, the orchestrator authors against that diff, then `ship.py` embeds the note in the PR body and writes the durable copy from the same point.
- Keep a durable committed copy, authored once from that single stable-HEAD step (Decision 2).

### Surfaces in scope
- `skills/implement/SKILL.md` (Step 7a Phase A staging, Step 8 compose, HEAD-drift reassessment prose)
- `skills/implement/references/architectural-guidelines-present.md`
- `python/larch/core/architectural_guidelines.py`
- `python/larch/implement/ship_guidelines.py`, `python/larch/implement/ship.py`
- Regression tests, including the #6114 rebase test extended to a moved-base case

### Open questions
- Exact orchestration seam between `ship.py`'s final rebase, orchestrator authoring, and compose. Resolved during plan drafting and review, not here.
