### FINDING_1: Design voter dispatch still hardcodes a Claude-first waterfall
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Panel Topology Auditor, Codex-dyn-Panel Topology Auditor
- **Severity**: major
- **Concern**: The plan still leaves `/design` voter dispatch on the old Claude voter-1 plus voter-2/3 waterfall shape, so config-only changes cannot produce the three Codex-primary voters, the semantic `VOTER_N_TOOL` labels, or the degraded single-Claude floor described in the acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `dispatch_voters` section: mirror `agent_voters.dispatch_voters` (all launched slots in one manifest, `launched_policies` shrink when both externals are down, `_semantic_label` for `VOTER_N_TOOL`, remove the always-on Claude side launch on the happy path)
  - From Codex-Arch: Add a firm plan step for dispatch_voters to build all three voter slots from design.plan_voters through the shared waterfall when any external is available, emit semantic VOTER_N_TOOL labels, and keep the dedicated Claude launch only in the both-externals-down floor.
  - From Cursor-Innovation: Extend plan_review_panel.py to refactor dispatch_voters toward agent_voters.dispatch_voters: enqueue all launched slots in one manifest, use vote role, emit semantic VOTER_N_TOOL labels, and keep Claude-only launch solely for both-externals-down
  - From Codex-Innovation: Revise the plan to make dispatch_voters policy-driven for voter-1, voter-2, and voter-3 in the normal branch, all in the waterfall with model-role vote; keep the direct Claude launch only for the both-externals-down floor
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/review/plan_review_panel.py` step to refactor `dispatch_voters` to match `agent_voters.dispatch_voters` (#5837): all three slots from `design.plan_voters` through one waterfall manifest with `--model-role vote`; launch only voter-1 when both externals are down; emit semantic `VOTER_N_TOOL` labels from bindings. Prefer reusing/extending `agent_voters` over duplicating logic.
  - From Codex-Pragmatic: Add `--claude-read-tools-add-dir str(design)` to the plan-voter dispatch-waterfall args in the non-floor path.
  - From Cursor-Requirements: Add explicit `dispatch_voters` work: mirror `agent_voters.dispatch_voters` (all launched slots in one waterfall manifest, Codex→Cursor→Claude per policy, semantic `VOTER_N_TOOL` labels, per-slot archetype prompts, single-slot Claude floor when both externals are down); extend `_make_voter_prompt` or reuse agent_voters helpers
  - From Codex-Requirements: Add a firm python/larch/review/plan_review_panel.py dispatch_voters step: outside the both-externals-down floor, build the waterfall manifest from all three design.plan_voters policies, render Codex/Cursor/Claude prompt maps for every slot, remove the standalone Claude Popen/retry path for voter-1, and emit semantic VOTER_N_TOOL labels from the resolved policy/tool binding.
  - From Cursor-dyn-Panel Topology Auditor: Add an explicit dispatch_voters work item: build a three-slot manifest from voter_policies like python/larch/agents/agent_voters.py, emit semantic VOTER_N_TOOL labels, and keep the single-Claude floor only when both externals are down
  - From Codex-dyn-Panel Topology Auditor: Add firm plan bullets for plan_review_panel.dispatch_voters and plan_review_round: dispatch all three design voter slots from design.plan_voters through Codex then Cursor then Claude, keep the both-external-down single-Claude floor, and pass semantic v1/v2/v3 labels into tally


### FINDING_5: Planned test coverage still omits the external-dispatch voter contract
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Innovation, Cursor-dyn-Panel Topology Auditor
- **Severity**: minor
- **Concern**: The test plan still relies on the old two-row manifest and a standalone Claude voter-1 assertion, so the dispatch rewrite will either fail those tests or leave the regression untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add this test file to the plan testing strategy and update assertions for a three-row manifest, semantic output basenames, and both-externals-down single-Claude floor behavior
  - From Codex-Innovation: Add python/tests/agents/test_external_dispatch.py to the targeted test list and update expectations for three-slot Codex-primary waterfall plus both-externals-down single-voter floor
  - From Cursor-Innovation: Add python/tests/agents/test_external_dispatch.py to the targeted test list and update expectations for three-slot Codex-primary waterfall plus both-externals-down single-voter floor
  - From Cursor-dyn-Panel Topology Auditor: Add test_external_dispatch.py (or fold into test_plan_review_panel.py) to require all three voter slots in plan-voter-slots.ndjson under the Codex-primary registry


### FINDING_6: TRIVIAL dynamic synthesis still suppresses dyn-cursor when Codex is available
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-Panel Topology Auditor
- **Severity**: major
- **Concern**: The TRIVIAL dynamic-row synthesis still drops dyn-cursor in the presence of Codex, which can leave TRIVIAL review with no dynamic rows or the wrong dynamic shape instead of the acceptance-required dyn-cursor-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Change TRIVIAL synthesis to always emit dyn-cursor when cursor is available, and skip dyn-codex only; add a test with a non-empty scout manifest and both externals present
  - From Cursor-dyn-Panel Topology Auditor: Add an explicit change to emit dyn-cursor on TRIVIAL whenever Cursor is available, and drop only the Codex dynamic row on TRIVIAL


### FINDING_10: HARD panel tests do not verify resolved_model rows
- **Reviewer(s)**: Codex-dyn-Panel Topology Auditor
- **Severity**: minor
- **Concern**: The planned HARD panel tests only assert model_role, not the resolved_model rows required by the acceptance criteria, so the exact row-model contract remains unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Panel Topology Auditor: Add default-env assertions that HARD design and code manifests each contain exactly two Codex rows with resolved_model=config.CODEX_DEFAULT_MODEL and that review-role static/dynamic Codex rows resolve to config.CODEX_REVIEW_MODEL_DEFAULT


### FINDING_1: Voter-1 semantic labels still hardcoded
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The plan-review voter dispatch refactor still leaves voter-1 parse-rate retry, voter-status-block emission, and final tool attribution tied to legacy `claude` labels even when the slot output moves to semantic Codex paths, which will keep legacy vendor labels in tallying and calibration data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the plan_review_panel.dispatch_voters section to derive voter_1_tool (and prompt file) from bind_manifest_slot_outputs like agent_voters._state_from_bindings, and pass that semantic label through _parse_rate_retry and voter-status-block for all three slots
  - From Cursor-Innovation: In `dispatch_voters`, resolve all three slots through the same `_semantic_label` + `_state_from_bindings` pattern as `agent_voters`, remove happy-path `Popen` voter-1, and pass resolved semantic tools into `_parse_rate_retry` and final `VOTER_N_TOOL` emission (or reuse `_emit_final_kvs`); keep `claude` only on the both-externals-down floor branch


### FINDING_3: Integration tests still encode the old voter-1 contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: minor
- **Concern**: The planned test inventory misses review-round integration harnesses that still assert `VOTER_1_TOOL=claude`, `claude-vote-output.txt`, and `subprocess.Popen`-based happy-path dispatch, so CI can pass narrow panel tests while round-loop mocks keep testing deleted behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/tests/review/test_plan_review_round.py with expectations for three-row manifests, codex-*-vote-output basenames, and semantic VOTER_N_TOOL values
  - From Cursor-Innovation: Add an explicit test-plan bullet to rewrite or delete every Popen-based happy-path voter-dispatch test and assert `VOTER_1_TOOL=codex-validity` (or cursor/claude fallback labels) on the externals-present path


### FINDING_4: Prompt invariant smoke still hardcodes legacy prompt filenames
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: major
- **Concern**: The prompt-invariant harness still asserts legacy plan/design voter prompt basenames, so the new semantic prompt/output names can cause lint or CI failures even when the feature works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add scripts/test-prompt-template-invariants.sh, and its md if needed, to the plan. Update the plan-voter smoke to assert the new semantic prompt files or a happy-path manifest while preserving the Verify silently and Output ONLY vote lines checks.
  - From Codex-Requirements: Add ### UPDATED: scripts/test-prompt-template-invariants.sh and retarget the smoke assertions to the new policy-derived prompt files, or discover the generated prompt files from the voter manifest instead of hard-coded legacy names.


