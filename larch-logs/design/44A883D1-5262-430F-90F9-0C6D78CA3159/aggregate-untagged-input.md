### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review-runtime.md:226; skills/design/SKILL.md:321; docs/review-agents.md:115; python/larch/core/config.py:483
- **Concern**: Plan leaves plan-review routing prose stale after removing role overrides and changing MODERATE routing to terra (G-Md-1, G-Wire-3).. Scenario: /design instructions and registry documentation can still say HARD uses the default role or MODERATE uses luna, while dispatch launches review-role rows and terra models.
- **Proposed resolution**: Update these consumers and `review.panel` fallback prose, then rerun documentation synchronization checks.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/shared/topology.tsv:17
- **Concern**: Topology authority is moved to review_dispatch_panel.py, but the plan does not require that file to contain the exact value `three specialists per vendor`.. Scenario: `lint topology-rule-paths` checks the row value in its authority file and will fail.
- **Proposed resolution**: Add the exact phrase to a dispatch-module comment/docstring, or retain config.py as the authority.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py
- **Concern**: The topology row retarget does not add the required `three specialists per vendor` anchor string to the new runtime authority file. Scenario: `skills/shared/topology.tsv` will point `implement.review_and_fix.panel_hard` at `python/larch/review/review_dispatch_panel.py` with value `three specialists per vendor`, but that exact substring is not present in the file today. `python/cli.py generate topology-docs`, `python/cli.py generate check`, and `python/cli.py lint topology-rule-paths` all require the row value to appear verbatim in the runtime authority file, so the acceptance `generate check passes` step fails even if dispatch filtering is correct
- **Proposed resolution**: Add a stable topology anchor comment (or equivalent literal substring) containing `three specialists per vendor` in `review_dispatch_panel.py` when retargeting the row authority away from `config.py`

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/core/config.py:490-507; python/tests/core/test_external_role_defaults.py:61-64
- **Concern**: Static plan-review slot metadata remains `default` despite the all-`review` contract. Scenario: `external_defaults.slot_defaults("design.plan_review_panel")` continues exposing stale roles, and the existing test preserves them
- **Proposed resolution**: Set static Codex `SlotDefault.model_role` to `review` and update the assertion accordingly

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:321 and skills/design/references/plan-review-runtime.md:226
- **Concern**: /design authority docs still say HARD plan-review uses the Codex default role after override removal. Scenario: The plan removes `DIFFICULTY_CODEX_MODEL_ROLE_OVERRIDES["design.plan_review_panel"]` and aligns `plan_review_panel.py` waterfall `--model-role` to `review`, but it does not update the normative /design surfaces that operators and Step 3 load. Those files still state HARD uses the default role, so /design will document the pre-change contract while runtime dispatches all HARD Codex plan-review rows with `review`.
- **Proposed resolution**: Add `### UPDATED: skills/design/SKILL.md` and `### UPDATED: skills/design/references/plan-review-runtime.md` to state that all static Codex plan-review rows, including HARD pragmatic/requirements, use the `review` role (and MODERATE terra where model routing is described). Mirror the updated `docs/review-agents.md` design-review wording.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_panel.py:574-601
- **Concern**: Plan-review dispatch changes the role but does not pass the tier-specific Codex model. Scenario: Without `--default-model`, MODERATE and HARD review-role launches use luna instead of terra
- **Proposed resolution**: Add the tier mapping as `--default-model` and assert the actual waterfall arguments

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:105-110
- **Concern**: The testing strategy omits three pytest files required by acceptance. Scenario: Rendering, plan-scout, and skills-structure acceptance remains unverified
- **Proposed resolution**: Add `python/tests/rendering/test_rendering.py`, `python/tests/design/test_plan_scout.py`, and `python/tests/skills/_structure_review_specialized.py` to targeted pytest
