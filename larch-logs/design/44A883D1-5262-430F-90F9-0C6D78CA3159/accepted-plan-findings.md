### FINDING_2: Missing topology authority anchor
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Retargeting the topology authority to `review_dispatch_panel.py` without the exact `three specialists per vendor` anchor will cause topology generation and validation checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the exact phrase to a dispatch-module comment/docstring, or retain config.py as the authority.
  - From Cursor-Pragmatic: Add a stable topology anchor comment (or equivalent literal substring) containing `three specialists per vendor` in `review_dispatch_panel.py` when retargeting the row authority away from `config.py`


### FINDING_4: Tier-specific Codex model is not dispatched
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Changing the plan-review role without passing the tier-specific Codex model causes MODERATE and HARD review-role launches to use luna instead of terra.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add the tier mapping as `--default-model` and assert the actual waterfall arguments


### FINDING_5: Acceptance testing plan is incomplete
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The testing strategy omits the rendering, plan-scout, and skills-structure pytest files required by acceptance, leaving those suites unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add `python/tests/rendering/test_rendering.py`, `python/tests/design/test_plan_scout.py`, and `python/tests/skills/_structure_review_specialized.py` to targeted pytest


