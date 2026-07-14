### FINDING_1: Bootstrap coder-order test is stale
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Flipping the TRIVIAL coder waterfall to Cursor-first leaves `test_phase_coder_routes_difficulty_matrix` expecting Codex, causing the targeted or full test suite to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/state/test_bootstrap.py: change the TRIVIAL row to expected_coder cursor and include the file in the targeted pytest list
  - From Cursor-Innovation: Add ### UPDATED: python/tests/state/test_bootstrap.py: change the TRIVIAL/both-available row to expect cursor; include the file in Testing strategy
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/state/test_bootstrap.py`: change the `TRIVIAL` expected coder from `codex` to `cursor`
  - From Cursor-Requirements: Add ### UPDATED: python/tests/state/test_bootstrap.py changing the TRIVIAL row to expect cursor and include the file in the targeted pytest command


### FINDING_2: Difficulty-role test must reflect override removal
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Removing the HARD role overrides makes pragmatic and requirements use `review`, but the existing test still expects the default role.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote to ### UPDATED: python/tests/calibration/test_difficulty.py and rewrite pragmatic/requirements expectations to review; rename the test if default-role coverage is no longer the point


### FINDING_3: Plan-review HARD role assertions are stale
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: Removing the HARD role override makes all plan-review archetypes use `review`, while the existing HARD panel test expects pragmatic and requirements to use the default role.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Promote to ### UPDATED: python/tests/review/test_plan_review_panel.py: set roles_by_focus pragmatic and requirements to review and adjust the test name or docstring accordingly
  - From Codex-Arch: Make this a firm test update: expect review for all four Codex rows and expect --model-role review.
  - From Cursor-Innovation: Promote python/tests/review/test_plan_review_panel.py to firm UPDATED: set pragmatic/requirements roles to review and rename/adjust the default-role expectations


### FINDING_5: Public docs, prompts, and topology projections are stale
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Innovation
- **Severity**: major
- **Concern**: Shipped documentation, skill prompts, and topology metadata continue to describe four specialists, the retired reviewer, and old routing; topology synchronization may also fail linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update these consumers to describe three specialists, the new tiers, and Step 8 ownership of architectural assessment.
  - From Cursor-Innovation: Update the named public docs and topology.tsv, then regenerate docs/topology.md and verify the synchronized projections
  - From Cursor-Pragmatic: Add `### UPDATED: skills/shared/topology.tsv` (row `implement.review_and_fix.panel_hard`: value `three specialists per vendor`, composition drops `architectural-compliance`) and `### UPDATED: docs/topology.md` via `python3 python/cli.py generate topology-docs`
  - From Codex-Innovation: Update the named public docs and topology.tsv, then regenerate docs/topology.md and verify the synchronized projections


### FINDING_6: Standalone `/review` may lose architectural coverage
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: Removing the shared architectural-compliance reviewer from the common panel also removes architectural assessment from standalone `/review`, which has no Step 8 equivalent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make retirement site-specific: preserve the slot for /review and filter it only from /implement Step 5
  - From Codex-Pragmatic: Retire the slot only for /implement Step 5, or add a separate standalone-review panel/list that preserves this coverage


### FINDING_7: Agent default-model test is not updated
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `test_model_args_defaults_and_effort` hardcodes the old Codex model and will fail if the shared default changes to terra.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: python/tests/agents/test_agents.py`: default-model assertion uses `config.CODEX_DEFAULT_MODEL` (terra); TRIVIAL cursor case expects `grok-4.5`


### FINDING_8: Changing the shared Codex default broadens model behavior
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Changing `CODEX_DEFAULT_MODEL` affects unrelated default-role launches and model-less historical token rows, potentially changing their execution or pricing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Preserve CODEX_DEFAULT_MODEL and set only the MODERATE and HARD implement mappings to terra


### FINDING_9: Cursor TRIVIAL model test is not updated
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The Cursor implement-model test still expects `CURSOR_DEFAULT_MODEL` for TRIVIAL, but the new mapping selects `grok-4.5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: python/tests/agents/test_agents.py updating the TRIVIAL expected model to grok-4.5 or CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY[TRIVIAL] and list the file in targeted pytest


### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:769-777
- **Concern**: [SCOPE-REDUCTION] G-Wire-2/G-Wire-3: Changing CODEX_DEFAULT_MODEL broadens the feature beyond per-tier implement routing.. Scenario: CI, lint-fix, rebase, generic launches, and model-less token reports can switch from sol to terra unintentionally.
- **Proposed resolution**: Keep CODEX_DEFAULT_MODEL as sol and set explicit terra values in the moderate and hard implement-tier map.


### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/core/config.py:769-777; python/larch/report/report_tokens_cost.py:18; python/larch/report/tokens.py:1093
- **Concern**: [SCOPE-REDUCTION] Changing shared CODEX_DEFAULT_MODEL broadens the feature beyond per-tier implement routing. Scenario: Model-less historical Codex rows are repriced from gpt-5.6-sol to terra, and unrelated default-role callers also change
- **Proposed resolution**: Keep CODEX_DEFAULT_MODEL at sol and set terra only in the implement difficulty map, or decouple the legacy pricing fallback


### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/core/config.py:769-777
- **Concern**: [SCOPE-REDUCTION] Changing CODEX_DEFAULT_MODEL broadens a tier-specific routing change into unrelated defaults.. Scenario: Agent default-role launches and token-cost reports move from gpt-5.6-sol to terra; existing default snapshots fail and missing-model costs change.
- **Proposed resolution**: Keep CODEX_DEFAULT_MODEL at gpt-5.6-sol and set only the MODERATE and HARD implement mappings to gpt-5.6-terra.


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


