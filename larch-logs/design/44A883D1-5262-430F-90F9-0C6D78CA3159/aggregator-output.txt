### FINDING_1: Plan-review documentation remains stale
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Plan-review authority and registry documentation still describe the pre-change role/model routing, including HARD default-role behavior and MODERATE luna routing, while runtime dispatch uses review-role rows and terra models.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update these consumers and `review.panel` fallback prose, then rerun documentation synchronization checks.
  - From Cursor-Requirements: Add `### UPDATED: skills/design/SKILL.md` and `### UPDATED: skills/design/references/plan-review-runtime.md` to state that all static Codex plan-review rows, including HARD pragmatic/requirements, use the `review` role (and MODERATE terra where model routing is described). Mirror the updated `docs/review-agents.md` design-review wording.

### FINDING_2: Missing topology authority anchor
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Retargeting the topology authority to `review_dispatch_panel.py` without the exact `three specialists per vendor` anchor will cause topology generation and validation checks to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the exact phrase to a dispatch-module comment/docstring, or retain config.py as the authority.
  - From Cursor-Pragmatic: Add a stable topology anchor comment (or equivalent literal substring) containing `three specialists per vendor` in `review_dispatch_panel.py` when retargeting the row authority away from `config.py`

### FINDING_3: Stale static plan-review slot roles
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: Static plan-review slot metadata remains `default` despite the all-`review` contract, preserving stale roles in `external_defaults.slot_defaults("design.plan_review_panel")` and its test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Set static Codex `SlotDefault.model_role` to `review` and update the assertion accordingly

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
