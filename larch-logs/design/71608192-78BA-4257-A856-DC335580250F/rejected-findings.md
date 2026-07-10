### [Plan Review] FINDING_2

### FINDING_2: Direct forced plan-fidelity tests still assume a review.panel row
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The helper tests still encode the old behavior of appending a forced plan-fidelity row after a review.panel no-op, so they will fail once the plan disables that path even if the broader matrix tests are updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite the _append_forced_plan_fidelity_row direct tests to assert zero rows for review.panel (or delete them if prune fixtures are covered elsewhere); keep prune tests that use synthetic plan-fidelity-forced fixtures only when they do not assert panel policy


### [Plan Review] FINDING_3

### FINDING_3: Review-panel manifest attribution never sees the tier default model
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: Tier-specific review-panel routing can launch one Codex model while the manifest records another, so the new panel routing is not faithfully reflected in resolved-model metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Thread the tier default_model into _resolved_model_for_row or store it on each manifest row before writing JSON
  - From Codex-Innovation: Thread the tier default into the row-attribution helper, or set `resolved_model` from the same tier map before writing each Codex row.


### [Plan Review] FINDING_4

### FINDING_4: Voter manifest rows need routed Codex model metadata
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Voter rows do not capture which routed Codex model was actually used, so `/review` cannot record whether a tier used Luna or Terra.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a resolved_model or default_model field to voter rows and populate it from the tier-aware routing


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/agents/agent_waterfall.py:57-444
- **Concern**: [SCOPE-REDUCTION] Per-row default_model on dynamic manifest rows is unwired; review-role default is enough. Scenario: Plan tells _synthesize_dynamic_slots to write default_model=gpt-5.6-luna on rows, but Slot parsing and launch only forward global opts.default_model; row-level default_model is ignored today and the plan does not add per-slot forwarding
- **Proposed resolution**: Do not add per-row default_model fields unless agent_waterfall gains slot-level parsing and forwarding; for TRIVIAL Cursor-down emit model_role=review only and depend on CODEX_REVIEW_MODEL_DEFAULT=gpt-5.6-luna with omitted global --default-model


