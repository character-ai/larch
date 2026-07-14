### [Plan Review] FINDING_1

### FINDING_1: Plan-review documentation remains stale
- **Reviewer(s)**: Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: Plan-review authority and registry documentation still describe the pre-change role/model routing, including HARD default-role behavior and MODERATE luna routing, while runtime dispatch uses review-role rows and terra models.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update these consumers and `review.panel` fallback prose, then rerun documentation synchronization checks.
  - From Cursor-Requirements: Add `### UPDATED: skills/design/SKILL.md` and `### UPDATED: skills/design/references/plan-review-runtime.md` to state that all static Codex plan-review rows, including HARD pragmatic/requirements, use the `review` role (and MODERATE terra where model routing is described). Mirror the updated `docs/review-agents.md` design-review wording.


### [Plan Review] FINDING_3

### FINDING_3: Stale static plan-review slot roles
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Concern**: Static plan-review slot metadata remains `default` despite the all-`review` contract, preserving stale roles in `external_defaults.slot_defaults("design.plan_review_panel")` and its test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Set static Codex `SlotDefault.model_role` to `review` and update the assertion accordingly


